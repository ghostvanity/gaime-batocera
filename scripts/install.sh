#!/bin/bash
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SYSTEM_DIR="/userdata/system"
CONFIG_DIR="$SYSTEM_DIR/configs"
SCRIPTS_DIR="$SYSTEM_DIR/scripts"
SERVICES_DIR="$SYSTEM_DIR/services"
UDEV_DIR="/etc/udev/rules.d"
CONFIG_FILE="$CONFIG_DIR/gaime.conf"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$SYSTEM_DIR/gaime-backups/$TIMESTAMP"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this installer as root on Batocera." >&2
    exit 1
fi

mkdir -p "$CONFIG_DIR" "$SCRIPTS_DIR" "$SERVICES_DIR" "$UDEV_DIR" "$BACKUP_DIR"

backup_if_exists() {
    path="$1"
    if [ -e "$path" ]; then
        cp -a "$path" "$BACKUP_DIR/$(basename "$path")"
    fi
}

for path in \
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
    "$SCRIPTS_DIR/gaime_game_state.sh" \
    "$SERVICES_DIR/GAIME" \
    "$UDEV_DIR/99-gaime-lightgun.rules"; do
    backup_if_exists "$path"
done

for file in \
    gaime_virtual.py gaime_device.py gaime_protocol.py gaime_config.py \
    gaime_display.py gaime_native_collect.py gaime_auto_build.py \
    gaime_auto_send.py gaime_border_16x9.py; do
    cp -f "$ROOT/src/$file" "$SYSTEM_DIR/$file"
done

cp -f "$ROOT/batocera/gaime_watchdog.sh" "$SYSTEM_DIR/gaime_watchdog.sh"
cp -f "$ROOT/batocera/gaime_calibration_wizard.sh" "$SYSTEM_DIR/gaime_calibration_wizard.sh"
cp -f "$ROOT/batocera/gaime_game_state.sh" "$SCRIPTS_DIR/gaime_game_state.sh"
cp -f "$ROOT/batocera/GAIME" "$SERVICES_DIR/GAIME"
cp -f "$ROOT/batocera/99-gaime-lightgun.rules" "$UDEV_DIR/99-gaime-lightgun.rules"

chmod +x \
    "$SYSTEM_DIR/gaime_virtual.py" \
    "$SYSTEM_DIR/gaime_native_collect.py" \
    "$SYSTEM_DIR/gaime_auto_build.py" \
    "$SYSTEM_DIR/gaime_auto_send.py" \
    "$SYSTEM_DIR/gaime_border_16x9.py" \
    "$SYSTEM_DIR/gaime_watchdog.sh" \
    "$SYSTEM_DIR/gaime_calibration_wizard.sh" \
    "$SCRIPTS_DIR/gaime_game_state.sh" \
    "$SERVICES_DIR/GAIME"

if [ ! -f "$CONFIG_FILE" ]; then
    cp "$ROOT/config/gaime.conf.example" "$CONFIG_FILE"
    PORTS="$(PYTHONPATH="$SYSTEM_DIR" python3 "$SYSTEM_DIR/gaime_device.py" --ports 2>/dev/null || true)"
    P1="$(printf '%s\n' "$PORTS" | sed -n '1p')"
    P2="$(printf '%s\n' "$PORTS" | sed -n '2p')"
    [ -n "$P1" ] && sed -i "s#^P1_USB_PORT=.*#P1_USB_PORT=$P1#" "$CONFIG_FILE"
    [ -n "$P2" ] && sed -i "s#^P2_USB_PORT=.*#P2_USB_PORT=$P2#" "$CONFIG_FILE"
fi

python3 -m py_compile \
    "$SYSTEM_DIR/gaime_virtual.py" \
    "$SYSTEM_DIR/gaime_device.py" \
    "$SYSTEM_DIR/gaime_protocol.py" \
    "$SYSTEM_DIR/gaime_config.py" \
    "$SYSTEM_DIR/gaime_display.py" \
    "$SYSTEM_DIR/gaime_native_collect.py" \
    "$SYSTEM_DIR/gaime_auto_build.py" \
    "$SYSTEM_DIR/gaime_auto_send.py" \
    "$SYSTEM_DIR/gaime_border_16x9.py"

bash -n "$SYSTEM_DIR/gaime_watchdog.sh"
bash -n "$SYSTEM_DIR/gaime_calibration_wizard.sh"
bash -n "$SCRIPTS_DIR/gaime_game_state.sh"
bash -n "$SERVICES_DIR/GAIME"

udevadm control --reload-rules
udevadm trigger --subsystem-match=input 2>/dev/null || true

if command -v batocera-save-overlay >/dev/null 2>&1; then
    batocera-save-overlay
fi

batocera-services stop GAIME 2>/dev/null || true
batocera-services enable GAIME
batocera-services start GAIME

echo
echo "G'AIM'E support installed."
echo "Config: $CONFIG_FILE"
echo "Backup: $BACKUP_DIR"
echo "Log:    /userdata/system/logs/gaime.log"
echo
echo "If P1/P2 ports were not detected, connect the guns and run:"
echo "  $ROOT/scripts/configure-players.sh"
