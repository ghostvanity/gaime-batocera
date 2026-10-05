#!/bin/bash
set -eu

SYSTEM_DIR="/userdata/system"
PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script as root on Batocera." >&2
    exit 1
fi

batocera-services stop GAIME 2>/dev/null || true
batocera-services disable GAIME 2>/dev/null || true

rm -f \
    "$SYSTEM_DIR/gaime_virtual.py" \
    "$SYSTEM_DIR/gaime_device.py" \
    "$SYSTEM_DIR/gaime_protocol.py" \
    "$SYSTEM_DIR/gaime_config.py" \
    "$SYSTEM_DIR/gaime_display.py" \
    "$SYSTEM_DIR/gaime_native_collect.py" \
    "$SYSTEM_DIR/gaime_auto_build.py" \
    "$SYSTEM_DIR/gaime_auto_send.py" \
    "$SYSTEM_DIR/gaime_border_16x9.py" \
    "$SYSTEM_DIR/gaime_watchdog.sh" \
    "$SYSTEM_DIR/gaime_calibration_wizard.sh" \
    "$SYSTEM_DIR/scripts/gaime_game_state.sh" \
    "$SYSTEM_DIR/services/GAIME" \
    "/etc/udev/rules.d/99-gaime-lightgun.rules"

rm -f "$SYSTEM_DIR"/__pycache__/gaime_*.pyc
rmdir "$SYSTEM_DIR/__pycache__" 2>/dev/null || true

rm -f \
    /tmp/gaime_calibration.lock \
    /tmp/gaime_game_running

if [ "$PURGE" -eq 1 ]; then
    rm -f \
        "$SYSTEM_DIR/configs/gaime.conf" \
        "$SYSTEM_DIR/gaime_auto_calibration.json" \
        "$SYSTEM_DIR/gaime_auto_packets.txt" \
        "$SYSTEM_DIR/gaime_auto_packets.previous.txt" \
        "$SYSTEM_DIR/gaime_last_calibration_status.txt" \
        "$SYSTEM_DIR/logs/gaime.log" \
        "$SYSTEM_DIR/logs/gaime-calibration.log"

    rm -rf "$SYSTEM_DIR/gaime-calibration-profiles"
fi

udevadm control --reload-rules
if command -v batocera-save-overlay >/dev/null 2>&1; then
    batocera-save-overlay
fi

echo "G'AIM'E runtime files removed."
if [ "$PURGE" -eq 0 ]; then
    echo "Configuration and calibration profiles were preserved."
    echo "Use --purge to remove those too."
fi
