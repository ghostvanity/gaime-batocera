# Calibration

## User flow

From EmulationStation, hold **A + B + Start** on the gun to calibrate for two seconds.

The eight target locations are:

```text
15%,15%     50%,15%     85%,15%
15%,50%                 85%,50%
15%,85%     50%,85%     85%,85%
```

Each target receives three shots. The collector takes the median of recent pre-trigger pointer samples, then the builder rejects saturated samples, excessive three-shot spread, or obviously folded/inverted geometry.

## Per-gun safety

The bridge passes:

- `GAIME_TARGET_PLAYER`
- `GAIME_TARGET_USB_SYSFS`
- `GAIME_TARGET_PHYS`

to the wizard.

Both collector and sender match the selected physical USB parent. With two guns connected, an untargeted collector/sender refuses to guess.

## Generated runtime files

```text
/userdata/system/gaime_auto_calibration.json
/userdata/system/gaime_auto_packets.txt
/userdata/system/gaime_auto_packets.previous.txt
/userdata/system/gaime_last_calibration_status.txt
/userdata/system/gaime-calibration-profiles/P1.json
/userdata/system/gaime-calibration-profiles/P1.packets.txt
/userdata/system/gaime-calibration-profiles/P2.json
/userdata/system/gaime-calibration-profiles/P2.packets.txt
```

The profile files are for diagnostics/reproducibility. The applied native calibration is written to the physical gun.

## Target-grid status

The 15/50/85 percent grid is the grid used by the working implementation. It should be treated as an implementation choice rather than an asserted factory G'AIM'E constant unless stronger vendor evidence is found.
