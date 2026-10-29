# Changelog

## 0.1.11

- Fix the daily heating and hot-water energy totals: the 24 readings in Ariston's
  `p=1` report are rolling two-hour periods, not 24 readings for the current day.
- Sum only completed two-hour periods since local midnight (Home Assistant time
  zone), excluding energy from previous days and the unfinished period.
- Preserve the existing energy sensor entity IDs and all other Ariston entities.

## 0.1.10

- Add separate heating and hot-water daily energy totals from the API's hourly consumption sequences.
- Expose the new daily sensors as kWh `total_increasing` energy entities for Home Assistant statistics.
- Preserve the existing period-reading energy sensors without changing their values or entity IDs.

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
