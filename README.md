# Ariston Nimbus

Temporary fork of the Ariston Home Assistant integration with GALEVO/Nimbus DHW Boost support.

This integration uses the `ariston_nimbus` domain so it can run alongside the original `ariston` integration.

## Nimbus / GALEVO

Adds the DHW Boost switch and other entities from the GALEVO heat-pump changes in PR #489.

The Python API dependency is pinned to the tested companion branch commit until the upstream changes are released.

## Daily energy statistics

For metered Ariston devices, two additional sensors report the energy used since
local midnight:

- **Ariston Nimbus heating energy today** — central heating (CO)
- **Ariston Nimbus hot water energy today** — domestic hot water (CWU)

They sum the hourly readings in the Ariston API's `LAST_DAY` sequence and update
with the energy coordinator (every 60 minutes by default). Both are in kWh with
`total_increasing` state class and can be used for daily long-term statistics.
The source values reset for a new day. Home Assistant only starts recording
long-term statistics after these sensors are added, so prior days are not
backfilled and the first day of statistics may be partial. Availability
depends on energy data being provided by Ariston.

Existing `*total_energy_consumption` sensors remain unchanged. They expose the
last reading in the API sequence rather than a running total and should not be
used as cumulative counters for `utility_meter`.

To graph daily values, add a Statistics Graph card using the new sensors with
`period: day`, `stat_types: [change]` and `chart_type: bar`.
