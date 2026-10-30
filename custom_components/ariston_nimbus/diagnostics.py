"""Diagnostics support for Ariston Nimbus.

Besides the raw data the integration already polls, the diagnostics file
contains a one-off scan of the Ariston technical menu (``menuItems``). The
integration currently reads only two of those items (CH return temperature
and Wi-Fi signal strength); the scan shows which other operating parameters
the cloud exposes for a given heat pump, so they can be added as sensors.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .ariston_nimbus_api.const import SystemType
from .const import COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Range of technical-menu item ids queried when diagnostics are downloaded.
MENU_SCAN_FIRST_ID = 1
MENU_SCAN_LAST_ID = 500
MENU_SCAN_BATCH_SIZE = 50

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    "gw",
    "gwId",
    "gateway",
    "sn",
    "serialNumber",
    "serial_number",
    "email",
    "plantName",
    "name",
    "location",
    "address",
    "lat",
    "lon",
    "latitude",
    "longitude",
    "unique_id",
    "title",
}


async def _async_scan_menu_items(device: Any) -> dict[str, Any]:
    """Query the technical menu in batches and collect every returned item."""
    api = getattr(device, "api", None)
    if api is None or not hasattr(api, "async_get_menu_items_by_ids"):
        return {"error": "menu scan not supported by this API version"}

    found: list[dict[str, Any]] = []
    failed_batches: list[str] = []
    for start in range(
        MENU_SCAN_FIRST_ID, MENU_SCAN_LAST_ID + 1, MENU_SCAN_BATCH_SIZE
    ):
        end = min(start + MENU_SCAN_BATCH_SIZE - 1, MENU_SCAN_LAST_ID)
        try:
            items = await api.async_get_menu_items_by_ids(
                device.gw, list(range(start, end + 1))
            )
        except Exception as err:  # noqa: BLE001 - diagnostics must not fail
            _LOGGER.debug("Menu scan %s-%s failed: %s", start, end, err)
            failed_batches.append(f"{start}-{end}: {err}")
            continue
        found.extend(item for item in items if isinstance(item, dict))

    found.sort(key=lambda item: item.get("id") or 0)
    return {
        "scanned_ids": f"{MENU_SCAN_FIRST_ID}-{MENU_SCAN_LAST_ID}",
        "items_found": len(found),
        "items": found,
        "failed_batches": failed_batches,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.unique_id][COORDINATOR]
    device = coordinator.device

    diagnostics: dict[str, Any] = {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "device": {
            "system_type": getattr(device.system_type, "name", None),
            "whe_type": getattr(getattr(device, "whe_type", None), "name", None),
            "whe_model_type": getattr(device, "whe_model_type", None),
            "firmware_version": getattr(device, "firmware_version", None),
            "attributes": async_redact_data(
                dict(getattr(device, "attributes", {}) or {}), TO_REDACT
            ),
            "features": async_redact_data(
                dict(getattr(device, "features", {}) or {}), TO_REDACT
            ),
            "custom_features": {
                str(key): value
                for key, value in (getattr(device, "custom_features", {}) or {}).items()
            },
        },
        "properties": async_redact_data(
            dict(getattr(device, "data", {}) or {}), TO_REDACT
        ),
        "menu_items_polled": list(getattr(device, "menu_items", []) or []),
        "bus_errors": list(getattr(device, "bus_errors_list", []) or []),
    }

    if device.system_type == SystemType.GALEVO:
        diagnostics["menu_items_scan"] = await _async_scan_menu_items(device)

    return diagnostics
