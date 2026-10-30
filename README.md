# Ariston Nimbus

Temporary fork of the Ariston Home Assistant integration with GALEVO/Nimbus DHW Boost support.

This integration uses the `ariston_nimbus` domain so it can run alongside the original `ariston` integration.

## Nimbus / GALEVO

Adds the DHW Boost switch and other entities from the GALEVO heat-pump changes in PR #489.

The Python API dependency is pinned to the tested companion branch commit until the upstream changes are released.

## Operating parameters

GALEVO devices also expose:

- **heat generator on** — the cloud's `IsFlameOn` status (on heat pumps it
  indicates the heat generator is running)
- **zone heat request** — one binary sensor per zone
- **anti-legionella enabled / temperature / frequency** (diagnostic)
- **CH flow-return delta** — flow temperature minus return temperature

Entities whose value the cloud does not report for your device are not
created.

## Technical-menu scan and diagnostics

To find further heat-pump operating parameters, run the service
**Ariston Nimbus: Scan technical menu** (`ariston_nimbus.scan_menu_items`) from
Developer tools → Actions. It scans menu items 1–500 in the background (a few
minutes), shows a notification when finished and saves the result to
`ariston_nimbus_menu_scan.json` in the config folder.

Device page → ⋮ → **Download diagnostics** saves the polled data together with
the latest scan result. Credentials, gateway, serial number and names are
redacted.

## Daily energy statistics

For metered Ariston devices, two additional sensors report the energy used since
local midnight:

- **Ariston Nimbus heating energy today** — central heating (CO)
- **Ariston Nimbus hot water energy today** — domestic hot water (CWU)

They sum only the completed two-hour readings from local midnight in the
Ariston API's rolling `LAST_DAY` sequence. The API supplies up to 24 two-hour
readings, so summing the entire sequence includes previous days. Values update
with the energy coordinator (every 60 minutes by default), and the current,
unfinished two-hour period is not included. Both sensors use kWh and the
`total_increasing` state class for Home Assistant statistics. The sensors reset
to zero on the first energy-coordinator update after local midnight.
Home Assistant only starts recording
long-term statistics after these sensors are added, so prior days are not
backfilled and the first day of statistics may be partial. Availability
depends on energy data being provided by Ariston.

**Note:** Ariston reports only *completed* two-hour periods. The 22:00–24:00
period is therefore published after midnight and cannot be included in the
live "today" value before the date changes. For authoritative completed-day
totals, use the historical daily readings in the Ariston app. The HA live
sensor is best treated as the currently reported consumption since midnight,
not a guaranteed final full-day total.

If you used version 0.1.10, its daily sensors included earlier periods and
could have produced incorrect statistics. Inspect existing Home Assistant
statistics for those two sensors after upgrading.

Existing `*total_energy_consumption` sensors remain unchanged. They expose the
last reading in the API sequence rather than a running total and should not be
used as cumulative counters for `utility_meter`.

To graph daily values, add a Statistics Graph card using the new sensors with
`period: day`, `stat_types: [change]` and `chart_type: bar`.
