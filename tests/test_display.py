import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaime_display import parse_xrandr


SAMPLE = """\
DP-3 connected primary 2560x1440+0+0 (normal left inverted right x axis y axis) 597mm x 336mm
DP-4 connected 1366x768+2560+0 (normal left inverted right x axis y axis) 410mm x 230mm
HDMI-1 disconnected (normal left inverted right x axis y axis)
"""

MULTI_NO_PRIMARY = """\
HDMI-1 connected 1920x1080+0+0
DP-1 connected 2560x1440+1920+0
"""


class DisplayTests(unittest.TestCase):
    def test_primary_selected(self):
        result = parse_xrandr(SAMPLE)
        self.assertEqual(result["name"], "DP-3")
        self.assertEqual(result["width"], 2560)
        self.assertEqual(result["height"], 1440)
        self.assertEqual(result["x"], 0)

    def test_requested_secondary_selected(self):
        result = parse_xrandr(SAMPLE, "DP-4")
        self.assertEqual(result["name"], "DP-4")
        self.assertEqual(result["x"], 2560)
        self.assertEqual(result["width"], 1366)
    def test_multiple_without_primary_fails(self):
        with self.assertRaisesRegex(
        RuntimeError,
        "Multiple active displays detected",
    ):
            parse_xrandr(MULTI_NO_PRIMARY)


    def test_requested_output_overrides_missing_primary(self):
        result = parse_xrandr(
            MULTI_NO_PRIMARY,
            "DP-1",
        )

        self.assertEqual(result["name"], "DP-1")
        self.assertEqual(result["width"], 2560)
        self.assertEqual(result["x"], 1920)


if __name__ == "__main__":
    unittest.main()
