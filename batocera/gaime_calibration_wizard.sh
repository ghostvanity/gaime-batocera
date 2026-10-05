#!/bin/bash

LOCK="/tmp/gaime_calibration.lock"
LOG="/userdata/system/logs/gaime-calibration.log"
STATUS="/userdata/system/gaime_last_calibration_status.txt"
COLLECTOR="/userdata/system/gaime_native_collect.py"
BUILDER="/userdata/system/gaime_auto_build.py"
SENDER="/userdata/system/gaime_auto_send.py"
CAPTURE="/userdata/system/gaime_auto_calibration.json"
PACKETS="/userdata/system/gaime_auto_packets.txt"
PREVIOUS="/userdata/system/gaime_auto_packets.previous.txt"
PROFILE_DIR="/userdata/system/gaime-calibration-profiles"
TARGET_LABEL="${GAIME_TARGET_PLAYER:-GAIME}"

mkdir -p /userdata/system/logs "$PROFILE_DIR"
cleanup() { rm -f "$LOCK"; }
trap cleanup EXIT TERM INT

touch "$LOCK"
echo "Calibration started for ${TARGET_LABEL}: $(date)" > "$STATUS"
echo "====================================" >> "$LOG"
echo "$(date): Calibration requested" >> "$LOG"
echo "$(date): Target player: ${TARGET_LABEL}" >> "$LOG"
echo "$(date): Target USB: ${GAIME_TARGET_USB_SYSFS:-not-set}" >> "$LOG"
echo "$(date): Target phys: ${GAIME_TARGET_PHYS:-not-set}" >> "$LOG"

# Give the bridge time to exit and release physical interfaces.
sleep 2

echo "$(date): Starting target collection" >> "$LOG"
python3 "$COLLECTOR" >> "$LOG" 2>&1
RESULT=$?
if [ "$RESULT" -ne 0 ]; then
    echo "FAILED during collection for ${TARGET_LABEL}: $(date)" > "$STATUS"
    echo "$(date): Collection FAILED ($RESULT)" >> "$LOG"
    exit 10
fi

[ -f "$PACKETS" ] && cp -f "$PACKETS" "$PREVIOUS"

echo "$(date): Building calibration packets" >> "$LOG"
python3 "$BUILDER" >> "$LOG" 2>&1
RESULT=$?
if [ "$RESULT" -ne 0 ]; then
    echo "FAILED quality/geometry validation for ${TARGET_LABEL}: $(date)" > "$STATUS"
    echo "$(date): Packet build FAILED ($RESULT)" >> "$LOG"
    exit 20
fi

echo "$(date): Sending native calibration" >> "$LOG"
python3 "$SENDER" --send >> "$LOG" 2>&1
RESULT=$?
if [ "$RESULT" -ne 0 ]; then
    echo "FAILED sending calibration to ${TARGET_LABEL}: $(date)" > "$STATUS"
    echo "$(date): Calibration send FAILED ($RESULT)" >> "$LOG"
    exit 30
fi

# Keep the most recent successful capture/packet set per player for debugging.
[ -f "$CAPTURE" ] && cp -f "$CAPTURE" "$PROFILE_DIR/${TARGET_LABEL}.json"
[ -f "$PACKETS" ] && cp -f "$PACKETS" "$PROFILE_DIR/${TARGET_LABEL}.packets.txt"

echo "SUCCESS - native calibration applied to ${TARGET_LABEL}: $(date)" > "$STATUS"
echo "$(date): Native calibration completed successfully for ${TARGET_LABEL}" >> "$LOG"
sync
exit 0
