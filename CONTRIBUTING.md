# Contributing

Please keep changes reviewable and evidence-driven.

- Distinguish observed G'AIM'E protocol behavior from implementation choices.
- Add or update an offline test for packet/CRC/ACK changes.
- Do not add hardcoded local `/dev/input/event*`, `/dev/hidraw*`, display connector, resolution, or USB-port values to the generic source.
- Treat in-game hotplug as emulator-dependent unless demonstrated otherwise.
- Preserve the fail-closed rule for two-gun calibration: if a physical target cannot be identified, do not write native calibration.
- Include the Batocera version, architecture, display geometry, and one/two-gun configuration when reporting hardware issues.
