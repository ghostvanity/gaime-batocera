#!/usr/bin/env python3
"""Validate captured samples and build eight native G'AIM'E calibration frames."""

import json
import os
from statistics import median

from gaime_protocol import (
    build_calibration_frame,
    fraction_to_fixed,
    hid_to_fixed,
)

INPUT_FILE = "/userdata/system/gaime_auto_calibration.json"
OUTPUT_FILE = "/userdata/system/gaime_auto_packets.txt"
MAX_SPREAD = 1000

# Implementation grid used by the working 16:9 calibration flow.
EXPECTED_TARGETS = [
    ("top_left", 0.15, 0.15),
    ("top_center", 0.50, 0.15),
    ("top_right", 0.85, 0.15),
    ("middle_left", 0.15, 0.50),
    ("middle_right", 0.85, 0.50),
    ("bottom_left", 0.15, 0.85),
    ("bottom_center", 0.50, 0.85),
    ("bottom_right", 0.85, 0.85),
]


def load_capture(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_capture(data):
    targets = {target["name"]: target for target in data["targets"]}
    medians = {}

    for name, expected_x, expected_y in EXPECTED_TARGETS:
        if name not in targets:
            raise RuntimeError(f"Missing target: {name}")

        target = targets[name]
        actual_x = float(target["reference_fraction"]["x"])
        actual_y = float(target["reference_fraction"]["y"])
        if abs(actual_x - expected_x) > 0.0001 or abs(actual_y - expected_y) > 0.0001:
            raise RuntimeError(
                f"{name}: unexpected reference ({actual_x},{actual_y})"
            )

        shots = target["shots"]
        if len(shots) != 3:
            raise RuntimeError(f"{name}: expected 3 shots")

        xs = [int(shot["x"]) for shot in shots]
        ys = [int(shot["y"]) for shot in shots]
        for x, y in zip(xs, ys):
            if x <= 0 or x >= 10000 or y <= 0 or y >= 10000:
                raise RuntimeError(f"{name}: saturated/invalid sample ({x},{y})")

        x_spread = max(xs) - min(xs)
        y_spread = max(ys) - min(ys)
        print(f"{name:14} spread={x_spread}/{y_spread}")
        if x_spread > MAX_SPREAD or y_spread > MAX_SPREAD:
            raise RuntimeError(
                f"{name}: tracking too unstable (spread={x_spread}/{y_spread})"
            )

        medians[name] = (float(median(xs)), float(median(ys)))

    mx = lambda name: medians[name][0]
    my = lambda name: medians[name][1]

    if not mx("top_left") < mx("top_center") < mx("top_right"):
        raise RuntimeError("Top-row X geometry is inverted")
    if not mx("middle_left") < mx("middle_right"):
        raise RuntimeError("Middle-row X geometry is inverted")
    if not mx("bottom_left") < mx("bottom_center") < mx("bottom_right"):
        raise RuntimeError("Bottom-row X geometry is inverted")
    if not my("top_left") < my("middle_left") < my("bottom_left"):
        raise RuntimeError("Left-column Y geometry is inverted")
    if not my("top_center") < my("bottom_center"):
        raise RuntimeError("Center-column Y geometry is inverted")
    if not my("top_right") < my("middle_right") < my("bottom_right"):
        raise RuntimeError("Right-column Y geometry is inverted")

    print("\nSample geometry passed.\n")
    return targets


def build_output(targets):
    output_lines = []

    for index, (name, expected_x, expected_y) in enumerate(EXPECTED_TARGETS):
        target = targets[name]
        frame = build_calibration_frame(
            index,
            target["shots"],
            expected_x,
            expected_y,
        )

        header = f"CHUNK {index}: {name}"
        output_lines.extend([header, "-" * len(header)])

        for shot_index, shot in enumerate(target["shots"], start=1):
            raw_x = int(shot["x"])
            raw_y = int(shot["y"])
            fixed_x = hid_to_fixed(raw_x)
            fixed_y = hid_to_fixed(raw_y)
            output_lines.append(
                f"shot {shot_index}: raw=({raw_x},{raw_y}) "
                f"fixed=({fixed_x},{fixed_y}) "
                f"normalized=({fixed_x / 32767.0:.6f},"
                f"{fixed_y / 32767.0:.6f})"
            )

        base_x = fraction_to_fixed(expected_x)
        base_y = fraction_to_fixed(expected_y)
        packet_crc = int.from_bytes(frame[39:41], "little")
        output_lines.append(
            f"base: fixed=({base_x},{base_y}) "
            f"normalized=({base_x / 32767.0:.6f},"
            f"{base_y / 32767.0:.6f})"
        )
        output_lines.append(f"CRC16: 0x{packet_crc:04X}")
        output_lines.append(
            "frame[0:41]: " + " ".join(f"{byte:02x}" for byte in frame[:41])
        )
        output_lines.append("")

    return "\n".join(output_lines)


def main():
    data = load_capture(INPUT_FILE)
    targets = validate_capture(data)
    output = build_output(targets)
    temporary = OUTPUT_FILE + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(output)
    os.replace(temporary, OUTPUT_FILE)
    print("All 8 packets built successfully.\n")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
