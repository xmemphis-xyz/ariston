# Changelog

## 0.1.14

- Add heat-pump operating sensors read from the technical menu (found with the
  menu scan on a Nimbus Compact S NET R32): heat pump mode (Heating, Standby,
  Defrost, Freeze protection, …), heat pump outside air temperature, heat pump
  water flow temperature, CH flow temperature, zone humidity, CH backup
  resistance and HV input 1.
- Poll the extended menu items without retries and fall back to the basic items
  (signal strength) if the cloud rejects them, so other models keep working.
- Do not create the CH return temperature sensor when the device does not report
  it, nor humidity sensors for zones without a humidity sensor.
- Climate entities show an unknown current temperature instead of 0 °C for zones
  without a room sensor.
- Diagnostics now also redact the plant address and coordinates.

## 0.1.13

- Fix Download diagnostics hanging: the technical-menu scan no longer runs during
  the download. The Ariston cloud rejects requests containing unknown ids with
  HTTP 500, and retrying every batch with backoff took several minutes.
- New `ariston_nimbus.scan_menu_items` service runs the scan in the background
  (fail-fast requests, falls back to single ids for rejected batches, capped
  requests and run time). The result appears as a notification, is saved to
  `ariston_nimbus_menu_scan.json` in the config folder and is included in
  Download diagnostics.
- Operating entities added in 0.1.12 are no longer created when the cloud does
  not report their value for the device.
- Log an unknown weather code only once instead of on every update.
- Fix the device picker of the `create_vacation` and `set_item_by_id` services
  (it pointed at the original `ariston` integration).

## 0.1.12

- Add Home Assistant diagnostics (device page → Download diagnostics). Besides the
  data already polled, it scans technical-menu items 1–500 so further heat-pump
  operating parameters can be identified and added as sensors.
- Add GALEVO operating entities: heat generator on, per-zone heat request,
  anti-legionella enabled / temperature / frequency, and the CH flow–return
  temperature difference.
- New entities stay unavailable when the Ariston cloud does not report the
  underlying value; existing entity IDs are unchanged.

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
