#!/bin/bash
set -eu

SYSTEM_DIR="/userdata/system"
CONFIG_DIR="$SYSTEM_DIR/configs"
CONFIG_FILE="$CONFIG_DIR/gaime.conf"
DEVICE_HELPER="$SYSTEM_DIR/gaime_device.py"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script as root on Batocera." >&2
    exit 1
fi

mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_FILE" ]; then
    cp "$(dirname "$0")/../config/gaime.conf.example" "$CONFIG_FILE"
fi

PORTS="$(PYTHONPATH="$SYSTEM_DIR" python3 "$DEVICE_HELPER" --ports 2>/dev/null || true)"
P1="$(printf '%s\n' "$PORTS" | sed -n '1p')"
P2="$(printf '%s\n' "$PORTS" | sed -n '2p')"

if [ -z "$P1" ]; then
    echo "No complete G'AIM'E gun detected. Connect the gun(s) and retry." >&2
    exit 2
fi

set_key() {
    key="$1"
    value="$2"
    if grep -q "^${key}=" "$CONFIG_FILE"; then
        sed -i "s#^${key}=.*#${key}=${value}#" "$CONFIG_FILE"
    else
        echo "${key}=${value}" >> "$CONFIG_FILE"
    fi
}

set_key P1_USB_PORT "$P1"
set_key P2_USB_PORT "$P2"

echo "Configured player ports:"
echo "  P1: $P1"
if [ -n "$P2" ]; then
    echo "  P2: $P2"
else
    echo "  P2: (not detected)"
fi

echo "Restarting GAIME service..."
batocera-services stop GAIME 2>/dev/null || true
sleep 1
batocera-services start GAIME
