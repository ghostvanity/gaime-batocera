#!/usr/bin/env python3
"""Pure G'AIM'E native-calibration packet helpers (no hardware dependency)."""

import struct

HID_MAX = 10000.0
FIXED_MAX = 32767.0
CALIBRATION_HEADER = bytes([0x05, 0x21, 0x06])
ACK_HEADER = bytes([0x05, 0x01, 0x06])


def crc16(data):
    """CRC-16/MODBUS used by observed G'AIM'E calibration reports."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def hid_to_fixed(value):
    value = max(0.0, min(HID_MAX, float(value)))
    return int(round(value / HID_MAX * FIXED_MAX))


def fraction_to_fixed(value):
    return int(round(float(value) * FIXED_MAX))


def build_calibration_frame(index, shots, reference_x, reference_y):
    if not 0 <= index <= 7:
        raise ValueError("Calibration chunk index must be 0..7")
    if len(shots) != 3:
        raise ValueError("Each calibration target requires exactly three shots")

    packet = bytearray(64)
    packet[0:3] = CALIBRATION_HEADER
    packet[3:6] = b"\x00\x00\x00"
    packet[6] = index
    offset = 7

    for shot in shots:
        fixed_x = hid_to_fixed(shot["x"])
        fixed_y = hid_to_fixed(shot["y"])
        struct.pack_into("<i", packet, offset, fixed_x)
        offset += 4
        struct.pack_into("<i", packet, offset, fixed_y)
        offset += 4

    struct.pack_into("<i", packet, offset, fraction_to_fixed(reference_x))
    offset += 4
    struct.pack_into("<i", packet, offset, fraction_to_fixed(reference_y))
    offset += 4

    if offset != 39:
        raise AssertionError(f"Unexpected calibration packet offset: {offset}")

    packet_crc = crc16(packet[:39])
    packet[39:41] = packet_crc.to_bytes(2, "little")
    return bytes(packet)


def validate_calibration_frame(frame, expected_index):
    if len(frame) not in (41, 64):
        raise ValueError(f"Expected 41 or 64 bytes, got {len(frame)}")
    if frame[0:3] != CALIBRATION_HEADER:
        raise ValueError("Wrong calibration command header")
    if frame[3:6] != b"\x00\x00\x00":
        raise ValueError("Reserved calibration bytes are not zero")
    if frame[6] != expected_index:
        raise ValueError(
            f"Chunk index is {frame[6]}, expected {expected_index}"
        )
    calculated = crc16(frame[:39])
    received = int.from_bytes(frame[39:41], "little")
    if calculated != received:
        raise ValueError(
            f"Calibration CRC mismatch {calculated:04X} != {received:04X}"
        )
    return received


def validate_calibration_ack(reply, chunk_index):
    if len(reply) < 9:
        raise ValueError(f"Chunk {chunk_index}: ACK too short ({len(reply)} bytes)")
    if reply[0:3] != ACK_HEADER:
        raise ValueError(f"Chunk {chunk_index}: unexpected ACK header")
    if reply[3:6] != b"\x00\x00\x00":
        raise ValueError(f"Chunk {chunk_index}: reserved ACK bytes are not zero")
    if reply[6] != 0x01:
        raise ValueError(
            f"Chunk {chunk_index}: gun did not return success "
            f"(byte6=0x{reply[6]:02X})"
        )
    received_crc = int.from_bytes(reply[7:9], "little")
    calculated_crc = crc16(reply[:7])
    if received_crc != calculated_crc:
        raise ValueError(
            f"Chunk {chunk_index}: ACK CRC mismatch "
            f"received=0x{received_crc:04X} calculated=0x{calculated_crc:04X}"
        )
    return received_crc


def load_packet_file(path):
    packets = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line.startswith("frame[0:41]:"):
                continue
            packets.append(bytes.fromhex(line.split("]:", 1)[1].strip()))

    if len(packets) != 8:
        raise ValueError(f"Expected 8 calibration packets, found {len(packets)}")

    for index, frame in enumerate(packets):
        validate_calibration_frame(frame, index)
    return packets
