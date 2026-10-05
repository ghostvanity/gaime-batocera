#!/usr/bin/env python3
"""Draw the white 16:9 tracking border used during G'AIM'E calibration."""

import ctypes
import ctypes.util
import os
import signal
import time

from gaime_config import load_config
from gaime_display import get_border_thickness, get_display_geometry

os.environ.setdefault("DISPLAY", ":0")

x11 = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11"))
Display = ctypes.c_void_p
Window = ctypes.c_ulong


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


x11.XOpenDisplay.restype = Display
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XDefaultScreen.restype = ctypes.c_int
x11.XDefaultScreen.argtypes = [Display]
x11.XRootWindow.restype = Window
x11.XRootWindow.argtypes = [Display, ctypes.c_int]
x11.XCreateSimpleWindow.restype = Window
x11.XCreateSimpleWindow.argtypes = [
    Display, Window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
    ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong,
]
x11.XChangeWindowAttributes.argtypes = [
    Display, Window, ctypes.c_ulong, ctypes.POINTER(XSetWindowAttributes)
]
x11.XMapRaised.argtypes = [Display, Window]
x11.XDestroyWindow.argtypes = [Display, Window]
x11.XFlush.argtypes = [Display]
x11.XCloseDisplay.argtypes = [Display]

WHITE = 0xFFFFFF
CW_OVERRIDE_REDIRECT = 1 << 9
running = True


def stop_handler(_signum, _frame):
    global running
    running = False


def main():
    config = load_config()
    geometry = get_display_geometry(config)
    thickness = get_border_thickness(geometry, config)
    x = geometry["x"]
    y = geometry["y"]
    width = geometry["width"]
    height = geometry["height"]

    display = x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError("Could not open X display")

    screen = x11.XDefaultScreen(display)
    root = x11.XRootWindow(display, screen)
    windows = []

    def make_strip(left, top, strip_width, strip_height):
        win = x11.XCreateSimpleWindow(
            display, root, left, top, strip_width, strip_height,
            0, WHITE, WHITE,
        )
        attrs = XSetWindowAttributes()
        attrs.override_redirect = 1
        x11.XChangeWindowAttributes(
            display, win, CW_OVERRIDE_REDIRECT, ctypes.byref(attrs)
        )
        x11.XMapRaised(display, win)
        windows.append(win)

    make_strip(x, y, width, thickness)
    make_strip(x, y + height - thickness, width, thickness)
    make_strip(x, y + thickness, thickness, height - 2 * thickness)
    make_strip(
        x + width - thickness,
        y + thickness,
        thickness,
        height - 2 * thickness,
    )
    x11.XFlush(display)

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    try:
        while running:
            time.sleep(0.25)
    finally:
        for win in windows:
            x11.XDestroyWindow(display, win)
        x11.XFlush(display)
        x11.XCloseDisplay(display)


if __name__ == "__main__":
    main()
