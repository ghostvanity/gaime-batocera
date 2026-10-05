import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaime_protocol import (
    build_calibration_frame,
    crc16,
    validate_calibration_ack,
    validate_calibration_frame,
)


class ProtocolTests(unittest.TestCase):
    def test_known_ack_crc(self):
        ack = bytes.fromhex("05 01 06 00 00 00 01 06 11")
        self.assertEqual(crc16(ack[:7]), 0x1106)
        self.assertEqual(validate_calibration_ack(ack, 0), 0x1106)

    def test_bad_ack_success_flag_rejected(self):
        ack = bytearray.fromhex("05 01 06 00 00 00 00 00 00")
        ack[7:9] = crc16(ack[:7]).to_bytes(2, "little")
        with self.assertRaises(ValueError):
            validate_calibration_ack(bytes(ack), 0)

    def test_build_and_validate_frame(self):
        frame = build_calibration_frame(
            3,
            [
                {"x": 1000, "y": 2000},
                {"x": 1100, "y": 2100},
                {"x": 1200, "y": 2200},
            ],
            0.15,
            0.50,
        )
        self.assertEqual(len(frame), 64)
        self.assertEqual(frame[:3], bytes.fromhex("05 21 06"))
        self.assertEqual(frame[6], 3)
        validate_calibration_frame(frame, 3)

    def test_wrong_index_rejected(self):
        frame = build_calibration_frame(
            2,
            [{"x": 100, "y": 100}] * 3,
            0.5,
            0.5,
        )
        with self.assertRaises(ValueError):
            validate_calibration_frame(frame, 1)


if __name__ == "__main__":
    unittest.main()
