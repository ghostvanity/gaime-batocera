#!/bin/bash

BRIDGE="/userdata/system/gaime_virtual.py"
LOCK="/tmp/gaime_calibration.lock"
LOG="/userdata/system/logs/gaime.log"
USB_ID="2e2c:0631"

BRIDGE_PID=""
BRIDGE_SIGNATURE=""

mkdir -p /userdata/system/logs

timestamp() { date; }

usb_signature() {
    lsusb -d "$USB_ID" 2>/dev/null | sort
}

usb_count() {
    local sig="$1"
    if [ -z "$sig" ]; then
        echo 0
    else
        printf '%s\n' "$sig" | wc -l
    fi
}

bridge_running() {
    [ -n "$BRIDGE_PID" ] && kill -0 "$BRIDGE_PID" 2>/dev/null
}

stop_bridge() {
    if bridge_running; then
        kill "$BRIDGE_PID" 2>/dev/null
        wait "$BRIDGE_PID" 2>/dev/null
    fi
    BRIDGE_PID=""
    BRIDGE_SIGNATURE=""
}

start_bridge() {
    local sig="$1"
    local count
    count="$(usb_count "$sig")"
    [ "$count" -le 0 ] && return

    echo "$(timestamp): $count G'AIM'E gun(s) detected - starting bridge" >> "$LOG"
    python3 "$BRIDGE" >> "$LOG" 2>&1 &
    BRIDGE_PID=$!
    BRIDGE_SIGNATURE="$sig"
}

cleanup() {
    trap - EXIT TERM INT
    stop_bridge
    exit 0
}
trap cleanup TERM INT EXIT

# Kill an orphaned bridge left by a previously interrupted watchdog.
for stale_pid in $(pgrep -f "^python3 ${BRIDGE}$" 2>/dev/null); do
    kill "$stale_pid" 2>/dev/null
done
sleep 0.5

while true; do
    CURRENT_SIGNATURE="$(usb_signature)"
    CURRENT_COUNT="$(usb_count "$CURRENT_SIGNATURE")"

    if [ -e "$LOCK" ]; then
        if bridge_running; then
            echo "$(timestamp): Calibration lock active - stopping bridge" >> "$LOG"
            stop_bridge
        fi
        sleep 0.5
        continue
    fi

    if [ "$CURRENT_COUNT" -eq 0 ]; then
        if bridge_running; then
            echo "$(timestamp): No G'AIM'E guns detected - stopping bridge" >> "$LOG"
            stop_bridge
        fi
        sleep 0.5
        continue
    fi

    if ! bridge_running; then
        start_bridge "$CURRENT_SIGNATURE"
        sleep 0.5
        continue
    fi

    if [ "$CURRENT_SIGNATURE" != "$BRIDGE_SIGNATURE" ]; then
        OLD_COUNT="$(usb_count "$BRIDGE_SIGNATURE")"
        echo "$(timestamp): G'AIM'E topology changed (${OLD_COUNT} -> ${CURRENT_COUNT}) - restarting bridge" >> "$LOG"
        stop_bridge
        sleep 0.75
        CURRENT_SIGNATURE="$(usb_signature)"
        [ -n "$CURRENT_SIGNATURE" ] && start_bridge "$CURRENT_SIGNATURE"
    fi

    sleep 0.5
done
