# Native calibration protocol notes

This document separates behavior observed on the tested G'AIM'E guns from choices made by this Batocera implementation.

## Observed / experimentally verified

### USB/HID layout

- VID: `0x2e2c`
- PID: `0x0631`
- Interface 0: keyboard/buttons
- Interface 1: absolute pointer/trigger
- Interface 2: vendor/config channel used for calibration
- Pointer axes: `ABS_X`, `ABS_Y`, range `0..10000`
- Pointer trigger: `BTN_TOUCH`

### Calibration write

Eight HID reports are sent to interface 2. Each transfer is 64 bytes, with the first 41 bytes meaningful:

| Byte(s) | Meaning |
|---|---|
| 0..2 | `05 21 06` command header |
| 3..5 | zero/reserved |
| 6 | chunk index `0..7` |
| 7..30 | three X/Y sample pairs, signed 32-bit little-endian |
| 31..38 | reference X/Y pair, signed 32-bit little-endian |
| 39..40 | CRC-16/MODBUS over bytes 0..38 |
| 41..63 | zero padding for the 64-byte HID write |

Coordinates in the native packet are represented on a `0..32767` scale.

### ACK

A successful reply observed from the gun begins:

```text
05 01 06 00 00 00 01 06 11
```

The implementation validates:

- header `05 01 06`;
- reserved bytes 3..5 are zero;
- byte 6 is success (`01`);
- bytes 7..8 are CRC-16/MODBUS over bytes 0..6.

The observed ACK CRC is `0x1106`.

### Empirical effect

Writing a complete accepted eight-chunk dataset changes the physical gun's raw pointer geometry. Calibration therefore belongs to the selected physical gun, not merely the virtual Batocera device.

## Implementation choices / not claimed as vendor constants

- 15/50/85 percent reference target grid.
- Three shots per target.
- Median of the recent pre-trigger sample window.
- Maximum three-shot spread of 1000 raw units.
- Bridge smoothing/deadzone/jump-rejection constants.
- 30 ms trigger-position latch.

## Reverse-engineering context

Public G'AIM'E reverse-engineering by Matt Kanwisher was useful background:

https://github.com/mattkanwisher/gaime_mods

No files from that repository are vendored here. Future contributors should verify applicable licensing/permission before copying code from external projects.
