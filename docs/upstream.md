# Batocera upstream notes

This repository is a working userspace release candidate, not yet a Batocera Buildroot package.

A likely upstream path is to adapt the project into Batocera's existing device-specific lightgun package structure under:

```text
package/batocera/controllers/guns/
```

Before proposing upstream integration:

1. keep hardware/protocol logic separated from install paths and local cabinet configuration;
2. retain offline tests for CRC/frame/ACK behavior;
3. document every empirically chosen constant;
4. avoid embedding a particular display connector, resolution, or USB port;
5. decide whether Batocera should own the virtual-device lifecycle instead of the current watchdog;
6. decide how G'AIM'E-specific settings should surface in EmulationStation;
7. test on more than one Batocera release/architecture and more than one display resolution;
8. choose a project license.

The current `src/` modules are deliberately separated so maintainers can review the protocol and device-discovery behavior without first reviewing installer glue.
