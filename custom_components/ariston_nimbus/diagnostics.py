"""Diagnostics support for Ariston Nimbus.

Contains the raw data the integration polls and, when the
``ariston_nimbus.scan_menu_items`` service has been run, the result of the
latest technical-menu scan. The scan itself runs from the service (in the
background), so downloading diagnostics is always quick.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import COORDINATOR, DOMAIN, MENU_SCAN_RESULT

_LOGGER = logging.getLogger(__name__)

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

    diagnostics["menu_items_scan"] = hass.data[DOMAIN][entry.unique_id].get(
        MENU_SCAN_RESULT,
        "not run yet - call the ariston_nimbus.scan_menu_items service first",
    )

    return diagnostics
