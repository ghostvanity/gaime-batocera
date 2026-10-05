# Changelog

## v0.1.0-rc1 - 2026-10-04

Initial release candidate based on the working Batocera implementation.

### Included
- Single- and dual-G'AIM'E input bridge.
- Stable P1/P2 assignment by configured physical USB port.
- Frontend hotplug detection and automatic bridge rebuild.
- Per-gun native calibration while both guns remain connected.
- G'AIM'E calibration packet validation and ACK validation.
- 16:9 calibration target/border support with display geometry discovered via xrandr.
- Batocera udev rule, service, watchdog, and game-state hook.
- Offline unit tests for protocol framing/CRC/ACK behavior.

### Known limitations
- In-game controller hotplug is emulator-dependent and is not supported as a guaranteed workflow.
- The calibration target grid (15/50/85 percent) is an implementation choice, not a recovered vendor constant.
- 4:3 cabinets and physically masked/bezel-constrained displays are not part of this release candidate.
- Tested hardware coverage is currently narrow; see README.md.
