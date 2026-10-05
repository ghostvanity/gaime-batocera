#!/usr/bin/env python3
"""Validate and optionally send native calibration packets to one G'AIM'E gun."""

import os
import select
import sys
import time

from gaime_device import find_config_hidraw
from gaime_protocol import load_packet_file, validate_calibration_ack

PACKET_FILE = "/userdata/system/gaime_auto_packets.txt"
TARGET_PLAYER = os.environ.get("GAIME_TARGET_PLAYER", "").strip()
TARGET_USB_SYSFS = os.environ.get("GAIME_TARGET_USB_SYSFS", "").strip()


def send_packets(packets):
    device, sysfs, usb_sysfs = find_config_hidraw(TARGET_USB_SYSFS)

    print(f"Found targeted config interface: {device}")
    if TARGET_PLAYER:
        print(f"Calibration target: {TARGET_PLAYER}")
    print(f"Sysfs: {sysfs}")
    if usb_sysfs:
        print(f"USB device: {usb_sysfs}")

    print("\n====================================")
    print("G'AIM'E NATIVE CALIBRATION TRANSFER")
    print("====================================\n")
    print(f"Device: {device}\n")
    print("Sending calibration chunks 0 -> 7")
    print("Gap between chunks: 200 ms\n")

    fd = os.open(device, os.O_RDWR | os.O_NONBLOCK)
    try:
        for index, frame in enumerate(packets):
            packet = frame + bytes(64 - len(frame))
            print(f"Chunk {index}/7...")
            written = os.write(fd, packet)
            if written != 64:
                raise RuntimeError(
                    f"Chunk {index}: only wrote {written}/64 bytes"
                )

            ready, _, _ = select.select([fd], [], [], 1.0)
            if not ready:
                raise RuntimeError(
                    f"Chunk {index}: NO ACK received; transfer aborted"
                )

            reply = os.read(fd, 64)
            ack_crc = validate_calibration_ack(reply, index)
            print(f"  ACK OK (CRC 0x{ack_crc:04X})")
            if index < 7:
                time.sleep(0.200)
    finally:
        os.close(fd)

    print("\n====================================")
    print("ALL 8 CHUNKS ACKNOWLEDGED")
    print("====================================\n")
    print("The selected gun accepted the complete calibration transfer.")


def main():
    packets = load_packet_file(PACKET_FILE)
    print("\nAll 8 calibration packets validated.\n")

    if "--send" not in sys.argv:
        print("DRY RUN COMPLETE.")
        print("Nothing was written to a gun.")
        print("Use --send to perform the transfer.")
        return

    send_packets(packets)


if __name__ == "__main__":
    main()
