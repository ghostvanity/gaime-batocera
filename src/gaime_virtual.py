#!/usr/bin/env python3
"""Bridge physical G'AIM'E HID interfaces into Batocera virtual lightguns."""

import math
import os
import select
import subprocess
import time
from collections import deque
from statistics import median

from evdev import AbsInfo, UInput, ecodes as e

from gaime_config import load_config
from gaime_device import (
    GAIME_PRODUCT,
    GAIME_VENDOR,
    assign_players,
    discover_gaime_guns,
    player_port_map,
)

MEDIAN_WINDOW = 3
DEADZONE_RADIUS = 300
MAX_SINGLE_JUMP = 1800
JUMP_CONFIRM_REPORTS = 3
TRIGGER_LATCH_SECONDS = 0.030

CALIBRATION_KEYS = {e.KEY_SPACE, e.KEY_B, e.KEY_Q}  # A + B + Start
BUTTON_MAP = {
    e.KEY_SPACE: e.BTN_RIGHT,   # A
    e.KEY_Q: e.BTN_MIDDLE,      # Start
    e.KEY_C: e.BTN_1,           # Coin
    e.KEY_B: e.BTN_2,           # B
}

CAL_LOCK = "/tmp/gaime_calibration.lock"
CAL_WIZARD = "/userdata/system/gaime_calibration_wizard.sh"
GAME_RUNNING_FLAG = "/tmp/gaime_game_running"


def emulator_running():
    return os.path.exists(GAME_RUNNING_FLAG)


class GaimeGun:
    def __init__(self, group, player):
        self.player = player
        self.uniq = group["uniq"]
        self.phys_base = group["phys_base"]
        self.pointer = group["pointer"]
        self.buttons = group["buttons"]
        self.usb_sysfs = group["usb_sysfs"]
        self.usb_port = group["usb_port"]

        self.x_info = self.pointer.absinfo(e.ABS_X)
        self.y_info = self.pointer.absinfo(e.ABS_Y)
        capabilities = {
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE, e.BTN_1, e.BTN_2],
            e.EV_ABS: [
                (
                    e.ABS_X,
                    AbsInfo(
                        value=self.x_info.value,
                        min=self.x_info.min,
                        max=self.x_info.max,
                        fuzz=0,
                        flat=0,
                        resolution=0,
                    ),
                ),
                (
                    e.ABS_Y,
                    AbsInfo(
                        value=self.y_info.value,
                        min=self.y_info.min,
                        max=self.y_info.max,
                        fuzz=0,
                        flat=0,
                        resolution=0,
                    ),
                ),
            ],
        }
        self.ui = UInput(
            capabilities,
            name=f"GAIME Lightgun P{player}",
            bustype=e.BUS_USB,
            vendor=GAIME_VENDOR,
            product=0x1631,
            version=1,
        )

        self.raw_x = self.x_info.value
        self.raw_y = self.y_info.value
        self.x_history = deque(maxlen=MEDIAN_WINDOW)
        self.y_history = deque(maxlen=MEDIAN_WINDOW)
        self.output_x = float(self.raw_x)
        self.output_y = float(self.raw_y)
        self.accepted_x = float(self.raw_x)
        self.accepted_y = float(self.raw_y)
        self.jump_count = 0
        self.trigger = 0
        self.previous_trigger = 0
        self.latched_x = self.output_x
        self.latched_y = self.output_y
        self.latch_until = 0.0
        self.calibration_key_state = {key: False for key in CALIBRATION_KEYS}
        self.calibration_combo_start = None

    def grab(self):
        self.pointer.grab()
        self.buttons.grab()

    def process_position(self, now):
        candidate_x = float(median(self.x_history))
        candidate_y = float(median(self.y_history))
        jump_distance = math.hypot(
            candidate_x - self.accepted_x,
            candidate_y - self.accepted_y,
        )

        if jump_distance > MAX_SINGLE_JUMP:
            self.jump_count += 1
            if self.jump_count < JUMP_CONFIRM_REPORTS:
                candidate_x = self.accepted_x
                candidate_y = self.accepted_y
            else:
                self.accepted_x = candidate_x
                self.accepted_y = candidate_y
                self.jump_count = 0
        else:
            self.accepted_x = candidate_x
            self.accepted_y = candidate_y
            self.jump_count = 0

        dx = self.accepted_x - self.output_x
        dy = self.accepted_y - self.output_y
        distance = math.hypot(dx, dy)
        if distance > DEADZONE_RADIUS:
            excess = distance - DEADZONE_RADIUS
            ratio = excess / distance
            self.output_x += dx * ratio
            self.output_y += dy * ratio

        if self.trigger and not self.previous_trigger:
            self.latched_x = self.output_x
            self.latched_y = self.output_y
            self.latch_until = now + TRIGGER_LATCH_SECONDS

        if now < self.latch_until:
            final_x, final_y = self.latched_x, self.latched_y
        else:
            final_x, final_y = self.output_x, self.output_y

        self.ui.write(e.EV_ABS, e.ABS_X, int(final_x))
        self.ui.write(e.EV_ABS, e.ABS_Y, int(final_y))
        self.ui.write(e.EV_KEY, e.BTN_LEFT, self.trigger)
        self.ui.syn()
        self.previous_trigger = self.trigger

    def handle_pointer(self):
        for event in self.pointer.read():
            if event.type == e.EV_ABS:
                if event.code == e.ABS_X:
                    self.raw_x = event.value
                elif event.code == e.ABS_Y:
                    self.raw_y = event.value
            elif event.type == e.EV_KEY and event.code == e.BTN_TOUCH:
                self.trigger = 1 if event.value else 0
            elif event.type == e.EV_SYN and event.code == e.SYN_REPORT:
                self.x_history.append(self.raw_x)
                self.y_history.append(self.raw_y)
                self.process_position(time.monotonic())

    def handle_buttons(self):
        for event in self.buttons.read():
            if event.type != e.EV_KEY or event.code not in BUTTON_MAP:
                continue

            if event.code in self.calibration_key_state and event.value != 2:
                self.calibration_key_state[event.code] = event.value == 1

            # Linux key autorepeat is not a new press.
            if event.value == 2:
                continue

            # At EmulationStation, reserve A/B/Start for the calibration chord.
            if not emulator_running() and event.code in CALIBRATION_KEYS:
                continue

            self.ui.write(
                e.EV_KEY,
                BUTTON_MAP[event.code],
                1 if event.value == 1 else 0,
            )
            self.ui.syn()

    def calibration_requested(self):
        if emulator_running() or not all(self.calibration_key_state.values()):
            self.calibration_combo_start = None
            return False

        if self.calibration_combo_start is None:
            self.calibration_combo_start = time.monotonic()
            return False

        return time.monotonic() - self.calibration_combo_start >= 2.0

    def close(self):
        for dev in (self.pointer, self.buttons):
            try:
                dev.ungrab()
            except Exception:
                pass
        for dev in (self.pointer, self.buttons):
            try:
                dev.close()
            except Exception:
                pass
        try:
            self.ui.close()
        except Exception:
            pass


def main():
    config = load_config()
    groups = discover_gaime_guns()
    if not groups:
        raise RuntimeError("Could not find a complete G'AIM'E pointer/button pair")

    assignments = assign_players(groups, player_port_map(config))
    guns = []

    try:
        for player, group in assignments:
            gun = GaimeGun(group, player)
            gun.grab()
            guns.append(gun)
            print(
                f"\nP{player}: uniq={gun.uniq or '(none)'} "
                f"phys={gun.phys_base}"
            )
            print(f"  Buttons: {gun.buttons.path}")
            print(f"  Pointer: {gun.pointer.path}")
            print(f"  USB: {gun.usb_sysfs}")
            print(f"  Player port: {gun.usb_port} -> P{player}")
            print(
                f"  Range: X {gun.x_info.min}-{gun.x_info.max}, "
                f"Y {gun.y_info.min}-{gun.y_info.max}"
            )
            print(f"  Virtual: {gun.ui.device} - GAIME Lightgun P{player}")

        print(f"\n{len(guns)} G'AIM'E lightgun(s) active.")
        print("Mappings:")
        print("  Trigger -> BTN_LEFT")
        print("  A       -> BTN_RIGHT")
        print("  Start   -> BTN_MIDDLE")
        print("  Coin    -> BTN_1")
        print("  B       -> BTN_2\n")
        print("A+B+Start calibrates the physical gun that initiated the combo.")
        print("Ctrl+C to stop.\n")

        fd_map = {}
        for gun in guns:
            fd_map[gun.pointer.fd] = (gun, "pointer")
            fd_map[gun.buttons.fd] = (gun, "buttons")

        while True:
            readable, _, _ = select.select(list(fd_map), [], [], 0.01)
            for fd in readable:
                gun, kind = fd_map[fd]
                try:
                    if kind == "pointer":
                        gun.handle_pointer()
                    else:
                        gun.handle_buttons()
                except OSError as exc:
                    print(
                        f"P{gun.player}: physical device disappeared: {exc}",
                        flush=True,
                    )
                    raise KeyboardInterrupt

            for gun in guns:
                if not gun.calibration_requested():
                    continue
                print(
                    f"P{gun.player}: A+B+Start held - starting G'AIM'E calibration",
                    flush=True,
                )
                with open(CAL_LOCK, "w", encoding="utf-8"):
                    pass
                calibration_env = {
                    **os.environ,
                    "GAIME_TARGET_PLAYER": f"P{gun.player}",
                    "GAIME_TARGET_USB_SYSFS": gun.usb_sysfs,
                    "GAIME_TARGET_PHYS": gun.phys_base,
                }
                subprocess.Popen(
                    [CAL_WIZARD],
                    env=calibration_env,
                    start_new_session=True,
                )
                raise KeyboardInterrupt

    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopping G'AIM'E bridge...")
        for gun in guns:
            gun.close()
        print("Physical interfaces released.")


if __name__ == "__main__":
    main()
