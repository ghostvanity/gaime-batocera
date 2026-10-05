#!/usr/bin/env python3
"""Collect three raw shots at each of eight reference targets."""

import ctypes
import ctypes.util
import json
import os
import signal
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from statistics import median

from evdev import ecodes as e

from gaime_config import load_config
from gaime_device import find_gaime_pointer
from gaime_display import get_border_thickness, get_display_geometry

OUTPUT_FILE = "/userdata/system/gaime_auto_calibration.json"
TARGET_PLAYER = os.environ.get("GAIME_TARGET_PLAYER", "").strip()
TARGET_USB_SYSFS = os.environ.get("GAIME_TARGET_USB_SYSFS", "").strip()
HISTORY_SIZE = 20
MIN_HISTORY = 8

# Implementation reference grid. These are not claimed as vendor constants.
TARGETS = [
    ("top_left", 0.15, 0.15),
    ("top_center", 0.50, 0.15),
    ("top_right", 0.85, 0.15),
    ("middle_left", 0.15, 0.50),
    ("middle_right", 0.85, 0.50),
    ("bottom_left", 0.15, 0.85),
    ("bottom_center", 0.50, 0.85),
    ("bottom_right", 0.85, 0.85),
]

os.environ.setdefault("DISPLAY", ":0")
x11 = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11"))
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XDefaultScreen.restype = ctypes.c_int
x11.XDefaultScreen.argtypes = [ctypes.c_void_p]
x11.XRootWindow.restype = ctypes.c_ulong
x11.XRootWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
x11.XCreateSimpleWindow.restype = ctypes.c_ulong
x11.XCreateSimpleWindow.argtypes = [
    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
    ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong,
]
x11.XMapRaised.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x11.XDestroyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x11.XFlush.argtypes = [ctypes.c_void_p]
x11.XCloseDisplay.argtypes = [ctypes.c_void_p]


class XSetWindowAttributes(ctypes.Structure):
    _fields_ = [
        ("background_pixmap", ctypes.c_ulong),
        ("background_pixel", ctypes.c_ulong),
        ("border_pixmap", ctypes.c_ulong),
        ("border_pixel", ctypes.c_ulong),
        ("bit_gravity", ctypes.c_int),
        ("win_gravity", ctypes.c_int),
        ("backing_store", ctypes.c_int),
        ("backing_planes", ctypes.c_ulong),
        ("backing_pixel", ctypes.c_ulong),
        ("save_under", ctypes.c_int),
        ("event_mask", ctypes.c_long),
        ("do_not_propagate_mask", ctypes.c_long),
        ("override_redirect", ctypes.c_int),
        ("colormap", ctypes.c_ulong),
        ("cursor", ctypes.c_ulong),
    ]


x11.XChangeWindowAttributes.argtypes = [
    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
    ctypes.POINTER(XSetWindowAttributes),
]
CW_OVERRIDE_REDIRECT = 1 << 9


def main():
    config = load_config()
    geometry = get_display_geometry(config)
    region_x = geometry["x"]
    region_y = geometry["y"]
    region_width = geometry["width"]
    region_height = geometry["height"]
    border_thickness = get_border_thickness(geometry, config)

    display = x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError("Could not open X display :0")
    screen = x11.XDefaultScreen(display)
    root = x11.XRootWindow(display, screen)

    def show_target(fx, fy):
        center_x = int(region_x + fx * region_width)
        center_y = int(region_y + fy * region_height)
        color = 0xFF0000
        horizontal = x11.XCreateSimpleWindow(
            display, root, center_x - 30, center_y - 3, 60, 6, 0, color, color
        )
        vertical = x11.XCreateSimpleWindow(
            display, root, center_x - 3, center_y - 30, 6, 60, 0, color, color
        )
        attrs = XSetWindowAttributes()
        attrs.override_redirect = 1
        for window in (horizontal, vertical):
            x11.XChangeWindowAttributes(
                display, window, CW_OVERRIDE_REDIRECT, ctypes.byref(attrs)
            )
            x11.XMapRaised(display, window)
        x11.XFlush(display)
        return horizontal, vertical, center_x, center_y

    def remove_target(windows):
        for window in windows:
            x11.XDestroyWindow(display, window)
        x11.XFlush(display)

    border_script = Path(__file__).with_name("gaime_border_16x9.py")
    border = subprocess.Popen(
        [sys.executable, str(border_script)],
        env={**os.environ, "DISPLAY": ":0"},
    )

    dev = None
    results = []
    try:
        dev, usb_sysfs = find_gaime_pointer(TARGET_USB_SYSFS)
        raw_x = dev.absinfo(e.ABS_X).value
        raw_y = dev.absinfo(e.ABS_Y).value
        history = deque(maxlen=HISTORY_SIZE)

        print(f"Found targeted G'AIM'E pointer: {dev.path} - {dev.name}")
        if TARGET_PLAYER:
            print(f"Calibration target: {TARGET_PLAYER}")
        print(f"Target USB device: {usb_sysfs}")
        print("\nG'AIM'E native calibration collector")
        print("====================================\n")
        print(f"Pointer: {dev.path}")
        print(
            f"Display: {geometry['name']} "
            f"{region_width}x{region_height}{region_x:+d}{region_y:+d}"
        )
        print("\nEach red target gets THREE shots.\n")
        print("Aim carefully, hold steady, then pull the trigger once.")
        print("The coordinate is taken from samples immediately before trigger-down.\n")

        dev.grab()
        try:
            for index, (name, fx, fy) in enumerate(TARGETS):
                windows = show_target(fx, fy)
                target_windows = windows[:2]
                pixel_x, pixel_y = windows[2], windows[3]
                print("\n------------------------------------")
                print(f"TARGET {index + 1}/8: {name.upper()}")
                print(f"Reference: {fx:.2f}, {fy:.2f}")
                print(f"Pixel: {pixel_x}, {pixel_y}")
                print("------------------------------------")

                shots = []
                trigger_down = False
                while len(shots) < 3:
                    event = dev.read_one()
                    if event is None:
                        time.sleep(0.001)
                        continue

                    if event.type == e.EV_ABS:
                        if event.code == e.ABS_X:
                            raw_x = event.value
                        elif event.code == e.ABS_Y:
                            raw_y = event.value
                    elif event.type == e.EV_SYN and event.code == e.SYN_REPORT:
                        history.append((raw_x, raw_y))
                    elif event.type == e.EV_KEY and event.code == e.BTN_TOUCH:
                        if event.value == 1 and not trigger_down:
                            trigger_down = True
                            if len(history) < MIN_HISTORY:
                                print("Hold steady a little longer and shoot again.")
                                continue
                            xs = [point[0] for point in history]
                            ys = [point[1] for point in history]
                            shot_x = int(median(xs))
                            shot_y = int(median(ys))
                            shots.append(
                                {
                                    "x": shot_x,
                                    "y": shot_y,
                                    "window_x_min": min(xs),
                                    "window_x_max": max(xs),
                                    "window_y_min": min(ys),
                                    "window_y_max": max(ys),
                                }
                            )
                            print(
                                f"Shot {len(shots)}/3: X={shot_x:5} Y={shot_y:5} "
                                f"pre-trigger range={max(xs)-min(xs)}/{max(ys)-min(ys)}"
                            )
                            history.clear()
                        elif event.value == 0:
                            trigger_down = False

                remove_target(target_windows)
                results.append(
                    {
                        "index": index,
                        "name": name,
                        "reference_fraction": {"x": fx, "y": fy},
                        "reference_pixel": {"x": pixel_x, "y": pixel_y},
                        "candidate_base_32767": {
                            "x": int(round(fx * 32767)),
                            "y": int(round(fy * 32767)),
                        },
                        "shots": shots,
                    }
                )
                time.sleep(0.75)
        finally:
            try:
                dev.ungrab()
            except OSError:
                pass
            dev.close()
            dev = None
    finally:
        try:
            border.terminate()
            border.wait(timeout=1)
        except Exception:
            try:
                border.kill()
            except Exception:
                pass
        x11.XCloseDisplay(display)
        if dev is not None:
            try:
                dev.close()
            except OSError:
                pass

    data = {
        "version": 1,
        "target_player": TARGET_PLAYER,
        "target_usb_sysfs": TARGET_USB_SYSFS,
        "screen": {
            "output": geometry["name"],
            "x": region_x,
            "y": region_y,
            "width": region_width,
            "height": region_height,
        },
        "playfield": {
            "x": region_x,
            "y": region_y,
            "width": region_width,
            "height": region_height,
            "ratio": "16:9",
            "border_thickness": border_thickness,
        },
        "targets": results,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)

    print("\n====================================")
    print("COLLECTION COMPLETE")
    print("====================================\n")
    for target in results:
        xs = [shot["x"] for shot in target["shots"]]
        ys = [shot["y"] for shot in target["shots"]]
        print(
            f"{target['index']} {target['name']:14} X={xs} Y={ys} "
            f"spread={max(xs)-min(xs)}/{max(ys)-min(ys)}"
        )
    print(f"\nSaved: {OUTPUT_FILE}")
    print("No calibration data has been written to the gun yet.")


if __name__ == "__main__":
    main()
