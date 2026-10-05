#!/usr/bin/env python3
"""G'AIM'E device/interface discovery shared by bridge and calibration tools."""

import glob
import os
import re
import sys

GAIME_VENDOR = 0x2E2C
GAIME_PRODUCT = 0x0631
VID = f"{GAIME_VENDOR:04X}"
PID = f"{GAIME_PRODUCT:04X}"


def _evdev():
    try:
        import evdev
        from evdev import InputDevice, ecodes as e
    except ImportError as exc:
        raise RuntimeError("python-evdev is required on the Batocera runtime") from exc
    return evdev, InputDevice, e


def natural_key(value):
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", value)
    ]


def find_usb_device_sysfs(sys_path):
    current = os.path.realpath(sys_path)

    while True:
        vendor_file = os.path.join(current, "idVendor")
        product_file = os.path.join(current, "idProduct")

        try:
            with open(vendor_file, "r", encoding="ascii") as handle:
                vendor = handle.read().strip().upper()
            with open(product_file, "r", encoding="ascii") as handle:
                product = handle.read().strip().upper()
            if vendor == VID and product == PID:
                return os.path.realpath(current)
        except OSError:
            pass

        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return None


def find_usb_device_sysfs_for_event(event_path):
    event_name = os.path.basename(event_path)
    result = find_usb_device_sysfs(
        f"/sys/class/input/{event_name}/device"
    )
    if result is None:
        raise RuntimeError(
            f"Could not resolve G'AIM'E USB device for {event_path}"
        )
    return result


def device_group_key(dev):
    phys = (dev.phys or "").strip()
    if "/input" in phys:
        phys = phys.rsplit("/input", 1)[0]

    # Prefer physical topology. G'AIM'E uniq has been observed changing
    # across reconnects on the tested hardware.
    if phys:
        return f"phys:{phys}"

    uniq = (dev.uniq or "").strip()
    if uniq:
        return f"uniq:{uniq}"

    return f"path:{dev.path}"


def discover_gaime_guns():
    evdev, InputDevice, e = _evdev()
    groups = {}
    gaime_keys = {e.KEY_SPACE, e.KEY_B, e.KEY_C, e.KEY_Q}

    for path in sorted(evdev.list_devices()):
        try:
            dev = InputDevice(path)
        except OSError:
            continue

        if dev.info.vendor != GAIME_VENDOR or dev.info.product != GAIME_PRODUCT:
            dev.close()
            continue

        caps = dev.capabilities(absinfo=False)
        abs_codes = caps.get(e.EV_ABS, [])
        key_codes = caps.get(e.EV_KEY, [])
        is_pointer = e.ABS_X in abs_codes and e.ABS_Y in abs_codes
        is_buttons = bool(gaime_keys.intersection(key_codes))

        if not is_pointer and not is_buttons:
            dev.close()
            continue

        key = device_group_key(dev)
        phys = (dev.phys or "")
        group = groups.setdefault(
            key,
            {
                "key": key,
                "uniq": (dev.uniq or "").strip(),
                "phys_base": (
                    phys.rsplit("/input", 1)[0]
                    if "/input" in phys
                    else phys
                ),
                "pointer": None,
                "buttons": None,
            },
        )

        slot = "pointer" if is_pointer else "buttons"
        if group[slot] is not None:
            group[slot].close()
        group[slot] = dev

    complete = []
    for group in groups.values():
        if group["pointer"] is None or group["buttons"] is None:
            for slot in ("pointer", "buttons"):
                if group[slot] is not None:
                    group[slot].close()
            continue

        group["usb_sysfs"] = find_usb_device_sysfs_for_event(
            group["pointer"].path
        )
        group["usb_port"] = os.path.basename(group["usb_sysfs"])
        complete.append(group)

    complete.sort(key=lambda group: natural_key(group["usb_port"]))
    return complete


def close_groups(groups):
    for group in groups:
        for slot in ("pointer", "buttons"):
            dev = group.get(slot)
            if dev is not None:
                try:
                    dev.close()
                except OSError:
                    pass


def player_port_map(config):
    mapping = {}
    if config.get("P1_USB_PORT"):
        mapping[config["P1_USB_PORT"]] = 1
    if config.get("P2_USB_PORT"):
        mapping[config["P2_USB_PORT"]] = 2
    return mapping


def assign_players(groups, configured_ports=None):
    configured_ports = configured_ports or {}
    assignments = []
    used_players = set()
    unassigned = []

    for group in groups:
        player = configured_ports.get(group["usb_port"])
        if player is not None and player not in used_players:
            assignments.append((player, group))
            used_players.add(player)
        else:
            unassigned.append(group)

    next_player = 1
    for group in unassigned:
        while next_player in used_players:
            next_player += 1
        assignments.append((next_player, group))
        used_players.add(next_player)
        next_player += 1

    assignments.sort(key=lambda item: item[0])
    return assignments


def find_gaime_pointer(target_usb_sysfs=""):
    evdev, InputDevice, e = _evdev()
    target_real = os.path.realpath(target_usb_sysfs) if target_usb_sysfs else ""
    matches = []

    for path in evdev.list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue

        if dev.info.vendor != GAIME_VENDOR or dev.info.product != GAIME_PRODUCT:
            dev.close()
            continue

        abs_codes = dev.capabilities(absinfo=False).get(e.EV_ABS, [])
        if e.ABS_X not in abs_codes or e.ABS_Y not in abs_codes:
            dev.close()
            continue

        usb_sysfs = find_usb_device_sysfs_for_event(path)
        if target_real and usb_sysfs != target_real:
            dev.close()
            continue

        matches.append((dev, usb_sysfs))

    if not matches:
        raise RuntimeError("Target G'AIM'E pointer interface not found")

    if not target_real and len(matches) > 1:
        for dev, _ in matches:
            dev.close()
        raise RuntimeError(
            "Multiple G'AIM'E pointers found but no target USB path was supplied"
        )

    dev, usb_sysfs = matches[0]
    for extra, _ in matches[1:]:
        extra.close()
    return dev, usb_sysfs


def find_config_hidraw(target_usb_sysfs=""):
    target_real = os.path.realpath(target_usb_sysfs) if target_usb_sysfs else ""
    matches = []

    for path in sorted(glob.glob("/dev/hidraw*")):
        name = os.path.basename(path)
        sysdev = f"/sys/class/hidraw/{name}/device"

        try:
            real = os.path.realpath(sysdev)
            with open(os.path.join(sysdev, "uevent"), "r", encoding="utf-8") as handle:
                info = handle.read().upper()
        except OSError:
            continue

        if VID not in info or PID not in info:
            continue
        if not re.search(r":1\.2/", real):
            continue

        usb_sysfs = find_usb_device_sysfs(sysdev)
        if target_real and usb_sysfs != target_real:
            continue
        matches.append((path, real, usb_sysfs))

    if not matches:
        if target_real:
            raise RuntimeError(
                f"Could not find config HID interface 2 for {target_real}"
            )
        raise RuntimeError("Could not find G'AIM'E HID interface 2")

    if not target_real and len(matches) > 1:
        raise RuntimeError(
            "Multiple G'AIM'E config interfaces found but no target USB path was supplied"
        )

    return matches[0]


def _cli_ports():
    groups = discover_gaime_guns()
    try:
        for group in groups:
            print(group["usb_port"])
    finally:
        close_groups(groups)


def _cli_describe():
    groups = discover_gaime_guns()
    try:
        for index, group in enumerate(groups, start=1):
            print(
                f"gun{index}: port={group['usb_port']} "
                f"uniq={group['uniq'] or '(none)'} "
                f"buttons={group['buttons'].path} "
                f"pointer={group['pointer'].path}"
            )
    finally:
        close_groups(groups)


if __name__ == "__main__":
    if "--ports" in sys.argv:
        _cli_ports()
    else:
        _cli_describe()
