#!/usr/bin/env python3
"""Display geometry discovery shared by calibration target and border tools."""

import re
import subprocess

from gaime_config import int_or_none, load_config

XRANDR_CONNECTED = re.compile(
    r"^(?P<name>\S+)\s+connected"
    r"(?P<primary>\s+primary)?"
    r"(?:\s+(?P<width>\d+)x(?P<height>\d+)"
    r"(?P<x>[+-]\d+)(?P<y>[+-]\d+))?"
)


def parse_xrandr(text, requested_output=""):
    outputs = []

    for line in text.splitlines():
        match = XRANDR_CONNECTED.match(line)
        if not match or match.group("width") is None:
            continue

        outputs.append(
            {
                "name": match.group("name"),
                "primary": bool(match.group("primary")),
                "x": int(match.group("x")),
                "y": int(match.group("y")),
                "width": int(match.group("width")),
                "height": int(match.group("height")),
            }
        )

    if not outputs:
        raise RuntimeError(
            "No active display geometry found in xrandr output"
        )

    if requested_output:
        for output in outputs:
            if output["name"] == requested_output:
                return output

        raise RuntimeError(
            f"Configured display output {requested_output!r} "
            "is not active"
        )

    # Single-monitor systems are unambiguous.
    if len(outputs) == 1:
        return outputs[0]

    primary_outputs = [
        output
        for output in outputs
        if output["primary"]
    ]

    # Multi-monitor system with one clearly-defined primary.
    if len(primary_outputs) == 1:
        return primary_outputs[0]

    active = "\n".join(
        f"  {output['name']} "
        f"{output['width']}x{output['height']}"
        f"{output['x']:+d}{output['y']:+d}"
        for output in outputs
    )

    if len(primary_outputs) > 1:
        raise RuntimeError(
            "Multiple active displays are marked primary.\n\n"
            f"Active outputs:\n{active}\n\n"
            "Set DISPLAY_OUTPUT in gaime.conf to the "
            "lightgun playfield display."
        )

    raise RuntimeError(
        "Multiple active displays detected and no primary "
        "display is set.\n\n"
        f"Active outputs:\n{active}\n\n"
        "Set DISPLAY_OUTPUT in gaime.conf to the "
        "lightgun playfield display."
    )


def get_display_geometry(config=None):
    config = config or load_config()

    width = int_or_none(config["DISPLAY_WIDTH"])
    height = int_or_none(config["DISPLAY_HEIGHT"])

    if width is not None and height is not None:
        x = int_or_none(config["DISPLAY_X"])
        y = int_or_none(config["DISPLAY_Y"])
        return {
            "name": config["DISPLAY_OUTPUT"] or "configured",
            "primary": True,
            "x": 0 if x is None else x,
            "y": 0 if y is None else y,
            "width": width,
            "height": height,
        }

    result = subprocess.run(
        ["xrandr", "--current"],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_xrandr(result.stdout, config["DISPLAY_OUTPUT"])


def get_border_thickness(geometry, config=None):
    config = config or load_config()
    configured = int_or_none(config["BORDER_THICKNESS"])
    if configured is not None:
        return configured
    return max(12, int(round(geometry["height"] * 0.036)))


if __name__ == "__main__":
    cfg = load_config()
    geometry = get_display_geometry(cfg)
    thickness = get_border_thickness(geometry, cfg)
    print(
        f"{geometry['name']} "
        f"{geometry['width']}x{geometry['height']}"
        f"{geometry['x']:+d}{geometry['y']:+d} "
        f"border={thickness}"
    )
