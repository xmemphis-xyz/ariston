# Changelog

## 0.1.9

- Prevent HTTP 500 responses from the optional `busErrors` endpoint from blocking all Ariston Nimbus entities during setup.
- Treat a failed initial energy-data refresh as non-fatal, allowing temperature, DHW and controls to load.
- Preserve periodic coordinators so optional diagnostic and energy data can recover after the cloud service is available again.

## 0.1.0

Initial Ariston Nimbus release.

- Separate `ariston_nimbus` Home Assistant integration domain.
- Can coexist with the original `ariston` integration.
- Nimbus / GALEVO DHW Boost support.
- Python API dependency pinned to the tested companion commit.
