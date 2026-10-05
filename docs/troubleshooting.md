# Troubleshooting

## Check that the service is running

```bash
pgrep -af gaime_watchdog
pgrep -af gaime_virtual.py
```

## Follow the bridge log

```bash
tail -f /userdata/system/logs/gaime.log
```

Expected with two configured guns:

```text
Player port: 1-2 -> P1
Player port: 1-9 -> P2
2 G'AIM'E lightgun(s) active.
```

## Show connected physical gun ports

```bash
PYTHONPATH=/userdata/system python3 /userdata/system/gaime_device.py --ports
```

If P1/P2 are wrong, rerun `scripts/configure-players.sh` from the repository or edit `/userdata/system/configs/gaime.conf`.

## Check udev classification

Find the virtual event number in `/proc/bus/input/devices`, then:

```bash
udevadm info -q property -n /dev/input/eventXX | \
grep -E 'ID_INPUT_GUN|ID_INPUT_MOUSE|ID_INPUT_GUN_NEED_BORDERS'
```

Expected:

```text
ID_INPUT_GUN=1
ID_INPUT_MOUSE=1
ID_INPUT_GUN_NEED_BORDERS=1
```

## Button-only evtest

```bash
evtest /dev/input/eventXX 2>/dev/null | \
grep --line-buffered 'EV_KEY'
```

Inside a game the expected virtual mappings are:

```text
A       -> BTN_RIGHT
B       -> BTN_2
Start   -> BTN_MIDDLE
Coin    -> BTN_1
Trigger -> BTN_LEFT
```

At EmulationStation, A/B/Start are reserved for the calibration chord and are suppressed by the bridge.

## Calibration log

```bash
cat /userdata/system/gaime_last_calibration_status.txt
tail -100 /userdata/system/logs/gaime-calibration.log
```

For a successful transfer, all chunks `0/7` through `7/7` should receive `ACK OK`.

## Hotplug during a game

The watchdog may recreate the virtual guns correctly, but the running emulator may not reopen the replacement `/dev/input/event*` devices. The supported recovery is:

1. reconnect the gun;
2. exit the game;
3. relaunch the game.
