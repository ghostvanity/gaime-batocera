#!/usr/bin/env python3
"""Small key=value configuration loader for the G'AIM'E Batocera tools."""

import os

CONFIG_PATH = os.environ.get(
    "GAIME_CONFIG_PATH",
    "/userdata/system/configs/gaime.conf",
)

DEFAULTS = {
    "P1_USB_PORT": "",
    "P2_USB_PORT": "",
    "DISPLAY_OUTPUT": "",
    "DISPLAY_X": "",
    "DISPLAY_Y": "",
    "DISPLAY_WIDTH": "",
    "DISPLAY_HEIGHT": "",
    "BORDER_THICKNESS": "",
}


def load_config(path=CONFIG_PATH):
    config = dict(DEFAULTS)

    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key not in config:
                    continue
                config[key] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass

    return config


def int_or_none(value):
    value = str(value).strip()
    if not value:
        return None
    return int(value)
