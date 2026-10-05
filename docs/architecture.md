# Architecture

The runtime intentionally has four layers.

## 1. Physical device discovery

`gaime_device.py` identifies G'AIM'E devices by VID/PID and groups the keyboard/button and absolute-pointer interfaces by their shared physical USB parent. This avoids relying on the HID `uniq` string, which changed across reconnects on the tested guns.

Configured USB topology names (for example `1-2`) map those physical guns to stable P1/P2 assignments.

## 2. Virtual lightgun bridge

`gaime_virtual.py` grabs the physical input interfaces and creates one uinput device per gun:

- `GAIME Lightgun P1`
- `GAIME Lightgun P2`

The udev rule marks these virtual devices as Batocera lightguns and requests borders.

The bridge translates the physical controls and applies the small position filter used by the tested setup.

## 3. Lifecycle / hotplug

`gaime_watchdog.sh` monitors the set of connected `2e2c:0631` devices. A topology change causes the bridge to exit/restart so the virtual devices match the current physical gun set.

The supported hotplug scope is the frontend. Emulators are expected to have the intended guns connected before game launch.

## 4. Native calibration

Holding A+B+Start on one gun at the frontend launches the calibration wizard with that gun's physical USB sysfs path in the environment.

The collector refuses to pick a different gun when a target path is supplied. The sender performs the same check for HID interface 2, so P1 calibration cannot accidentally be sent to P2 because of `/dev/hidraw*` enumeration order.

The bridge creates `/tmp/gaime_calibration.lock` before launching calibration. The watchdog keeps the bridge stopped while that lock exists and recreates the bridge after the wizard exits.
