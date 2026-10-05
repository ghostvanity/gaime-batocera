# G'AIM'E Lightgun support for Batocera

Community driver/bridge and native-calibration tooling for Tassei Denki G'AIM'E USB lightguns on Batocera.

**Status: v0.1.0-rc1 (release candidate).** Tested on a clean Batocera installation with two G'AIM'E guns, including per-gun native calibration, frontend hotplug, two-player gameplay, and reboot persistence.

The runtime architecture is intentionally kept simple while separating reusable device/protocol logic from Batocera-specific integration.

## Features

- One or two simultaneous G'AIM'E guns.
- Virtual Batocera lightguns (`GAIME Lightgun P1`, `GAIME Lightgun P2`).
- Stable player assignment by physical USB port.
- Trigger, A, B, Start, and Coin mapping.
- Input smoothing/jump rejection used by the tested setup.
- Frontend hotplug detection and automatic bridge restart.
- Native eight-point calibration written to the selected physical gun.
- P1 or P2 can be calibrated while both guns remain plugged in.
- Calibration sender validates packet structure, CRC, and every gun ACK.
- 16:9 calibration overlay with display geometry discovered from `xrandr` or overridden in config.

## Hardware identity

Observed retail G'AIM'E guns enumerate as:

- USB VID: `2e2c`
- USB PID: `0631`
- HID interface 0: keyboard/buttons
- HID interface 1: absolute pointer/trigger
- HID interface 2: vendor/config interface used by native calibration
- Pointer range: `ABS_X/ABS_Y` = `0..10000`

See [docs/protocol.md](docs/protocol.md) for the distinction between experimentally verified behavior and implementation choices.

## Tested setup

The current hardware-validated reference setup uses:

- Batocera on x86_64.
- Two wired G'AIM'E guns.
- 2560x1440 16:9 primary display plus a secondary display.
- Native calibration of each gun independently.
- Two-player lightgun gameplay with both guns connected before game launch.

The code now discovers display geometry instead of hardcoding 2560x1440, but other 16:9 resolutions should be treated as **not yet broadly tested**.

## Installation

SSH into Batocera as root, clone/copy this repository, then run:

```bash
cd gaime-batocera
./scripts/install.sh
```

The installer:

1. backs up an existing G'AIM'E installation if present;
2. installs the Python runtime files under `/userdata/system/`;
3. installs the Batocera service, watchdog, game-state hook, and udev rule;
4. creates `/userdata/system/configs/gaime.conf` if it does not already exist;
5. detects connected gun USB ports for P1/P2 when possible;
6. reloads udev and enables/restarts the `GAIME` Batocera service.

If the guns were not connected during installation, connect them and run:

```bash
./scripts/configure-players.sh
```

## Configuration

Runtime configuration is stored at:

```text
/userdata/system/configs/gaime.conf
```

Example:

```ini
P1_USB_PORT=1-2
P2_USB_PORT=1-9
DISPLAY_OUTPUT=
DISPLAY_X=
DISPLAY_Y=
DISPLAY_WIDTH=
DISPLAY_HEIGHT=
BORDER_THICKNESS=
```

Leaving the display fields blank lets the calibration tools use the active `xrandr` output. With multiple active displays, exactly one display must be marked primary, otherwise set `DISPLAY_OUTPUT` explicitly in `gaime.conf`.

`BORDER_THICKNESS` defaults to roughly 3.6% of the display height.

Player ports are Linux USB topology names, not G'AIM'E `uniq` values. The tested guns were observed changing `uniq` values after reconnects, while the cabinet's physical USB topology remained stable.

## Calibration

Calibration is available from the EmulationStation frontend only.

1. Keep both guns plugged in if using two-player mode.
2. Hold **A + B + Start** on the gun you want to calibrate for two seconds.
3. Shoot each red target three times.
4. The generated calibration packets are validated and sent only to that gun's HID config interface.
5. The watchdog automatically recreates the virtual guns after calibration completes.

Because A/B/Start form the calibration chord, those three physical buttons are reserved by this bridge while at the EmulationStation frontend. Inside a game they are forwarded normally.

See [docs/calibration.md](docs/calibration.md).

## Button mapping

| Physical control | Virtual input |
|---|---|
| Trigger | `BTN_LEFT` |
| A | `BTN_RIGHT` |
| B | `BTN_2` |
| Start | `BTN_MIDDLE` |
| Coin | `BTN_1` |

The physical trigger is observed as `BTN_TOUCH` on the G'AIM'E pointer interface and is translated to `BTN_LEFT` for Batocera/emulators.

## Hotplug behavior

At the frontend, adding/removing guns causes the bridge to rebuild automatically.

For games, the supported workflow is:

> Connect all guns/controllers you intend to use **before launching the game**.

Many emulators do not reopen input devices cleanly after they disappear while a game is running. If a gun is unplugged during gameplay, reconnect it, exit the game, and relaunch.

## Project layout

```text
src/        Python bridge, device discovery, display helpers, and calibration protocol
batocera/   service, watchdog, hooks, and udev integration
config/     example runtime configuration
docs/       protocol, calibration, architecture, troubleshooting, upstream notes
scripts/    installer, uninstall, and player-port configuration
tests/      offline protocol/display tests
```

## Development checks

On Linux, macOS, or Windows (no gun required for protocol tests):

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

On Batocera, also check shell syntax:

```bash
bash -n batocera/GAIME
bash -n batocera/gaime_watchdog.sh
bash -n batocera/gaime_calibration_wizard.sh
bash -n batocera/gaime_game_state.sh
bash -n scripts/install.sh
```

## Credits / reverse-engineering context

Special thanks to [Matt Kanwisher](https://github.com/mattkanwisher) for his public G'AIM'E reverse-engineering work and documentation:

- [mattkanwisher/gaime_mods](https://github.com/mattkanwisher/gaime_mods)

His research was useful background while investigating the G'AIM'E hardware and protocol.

This project does not vendor files from `gaime_mods`.

## Batocera upstreaming

Batocera already maintains device-specific lightgun packages under `package/batocera/controllers/guns/`. This repository is intentionally structured so the working userspace logic can be reviewed first, then reshaped into Batocera's package/build conventions if maintainers want it upstream.

See [docs/upstream.md](docs/upstream.md).

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0.

You may use, modify, and redistribute this software for noncommercial purposes.

Commercial use requires separate permission from the copyright holder.

The project may also be made available to the Batocera project under separate licensing terms for official integration and redistribution.

See [LICENSE](LICENSE) for the complete license terms.
