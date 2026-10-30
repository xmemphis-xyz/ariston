"""The Ariston integration."""

from __future__ import annotations

import json
import logging

import voluptuous as vol

from .ariston_nimbus_api import Ariston, DeviceAttribute, SystemType
from .ariston_nimbus_api.const import ARISTON_API_URL, ARISTON_USER_AGENT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_DEVICE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.util.unit_system import METRIC_SYSTEM

from .const import (
    API_URL_SETTING,
    API_USER_AGENT,
    BUS_ERRORS_COORDINATOR,
    BUS_ERRORS_SCAN_INTERVAL,
    COORDINATOR,
    DEFAULT_BUS_ERRORS_SCAN_INTERVAL_SECONDS,
    DEFAULT_ENERGY_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    ENERGY_COORDINATOR,
    ENERGY_SCAN_INTERVAL,
    MENU_SCAN_FILE,
    MENU_SCAN_RESULT,
)
from .coordinator import DeviceDataUpdateCoordinator
from .menu_scan import DEFAULT_FIRST_ID, DEFAULT_LAST_ID, async_scan_menu_items

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.WATER_HEATER,
]

SERVICE_SET_ITEM_BY_ID = "set_item_by_id"
ATTR_ITEM_ID = "item_id"
ATTR_ZONE = "zone"
ATTR_VALUE = "value"

SERVICE_SCAN_MENU_ITEMS = "scan_menu_items"
ATTR_FIRST_ID = "first_id"
ATTR_LAST_ID = "last_id"

SCAN_MENU_ITEMS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_FIRST_ID, default=DEFAULT_FIRST_ID): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=5000)
        ),
        vol.Optional(ATTR_LAST_ID, default=DEFAULT_LAST_ID): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=5000)
        ),
    }
)

SET_ITEM_BY_ID_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_ITEM_ID): cv.string,
        vol.Required(ATTR_ZONE): cv.positive_int,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
    }
)


async def _async_first_refresh_optional(
    coordinator: DeviceDataUpdateCoordinator, data_type: str
) -> None:
    """Fetch optional data without preventing the main integration from loading."""
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        _LOGGER.warning(
            "Optional Ariston %s data unavailable at startup (%s); "
            "continuing setup without it",
            data_type,
            err,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ariston from a config entry."""
    ariston = Ariston()
    try:
        api_url_setting = entry.data.get(API_URL_SETTING, ARISTON_API_URL)

        api_user_agent = entry.data.get(API_USER_AGENT, ARISTON_USER_AGENT)

        reponse = await ariston.async_connect(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            api_url_setting,
            api_user_agent,
        )
        if not reponse:
            _LOGGER.error(
                "Failed to connect to Ariston with device: %s",
                entry.data[CONF_DEVICE].get(DeviceAttribute.NAME),
            )
            raise ConfigEntryAuthFailed

        device = await ariston.async_hello(
            entry.data[CONF_DEVICE].get(DeviceAttribute.GW),
            hass.config.units is METRIC_SYSTEM,
        )
        if device is None:
            return False

        await device.async_get_features()

        scan_interval_seconds = entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
        )
        coordinator = DeviceDataUpdateCoordinator(
            hass, device, scan_interval_seconds, COORDINATOR, device.async_update_state
        )

        hass.data.setdefault(DOMAIN, {}).setdefault(
            entry.unique_id, {COORDINATOR: {}, ENERGY_COORDINATOR: {}}
        )
        hass.data[DOMAIN][entry.unique_id][COORDINATOR] = coordinator

        await coordinator.async_config_entry_first_refresh()

        bus_errors_scan_interval_seconds = entry.options.get(
            BUS_ERRORS_SCAN_INTERVAL, DEFAULT_BUS_ERRORS_SCAN_INTERVAL_SECONDS
        )
        bus_errors_coordinator = DeviceDataUpdateCoordinator(
            hass,
            device,
            bus_errors_scan_interval_seconds,
            BUS_ERRORS_COORDINATOR,
            device.async_get_bus_errors,
        )
        hass.data[DOMAIN][entry.unique_id][BUS_ERRORS_COORDINATOR] = (
            bus_errors_coordinator
        )
        await _async_first_refresh_optional(bus_errors_coordinator, "bus errors")

        if device.has_metering:
            energy_interval_minutes = entry.options.get(
                ENERGY_SCAN_INTERVAL, DEFAULT_ENERGY_SCAN_INTERVAL_MINUTES
            )
            energy_coordinator = DeviceDataUpdateCoordinator(
                hass,
                device,
                energy_interval_minutes * 60,
                ENERGY_COORDINATOR,
                device.async_update_energy,
            )
            hass.data[DOMAIN][entry.unique_id][ENERGY_COORDINATOR] = energy_coordinator
            await _async_first_refresh_optional(energy_coordinator, "energy")

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        entry.async_on_unload(entry.add_update_listener(update_listener))

        if device.system_type == SystemType.GALEVO:

            async def async_set_item_by_id_service(service_call):
                """Create a vacation on the target device."""
                device_id = service_call.data.get(ATTR_DEVICE_ID)
                item_id = service_call.data.get(ATTR_ITEM_ID)
                zone = service_call.data.get(ATTR_ZONE)
                value = service_call.data.get(ATTR_VALUE)

                device_registry = dr.async_get(hass)
                device = device_registry.devices[device_id]

                entry = hass.config_entries.async_get_entry(
                    next(iter(device.config_entries))
                )
                coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][
                    entry.unique_id
                ][COORDINATOR]
                await coordinator.device.async_set_item_by_id(item_id, value, zone)

            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_ITEM_BY_ID,
                async_set_item_by_id_service,
                schema=SET_ITEM_BY_ID_SCHEMA,
            )

            async def async_scan_menu_items_service(service_call):
                """Start a background scan of the technical menu."""
                await _async_start_menu_scan(hass, service_call)

            hass.services.async_register(
                DOMAIN,
                SERVICE_SCAN_MENU_ITEMS,
                async_scan_menu_items_service,
                schema=SCAN_MENU_ITEMS_SCHEMA,
            )
    except ConfigEntryAuthFailed:
        raise
    except Exception as error:
        _LOGGER.exception("")
        raise ConfigEntryNotReady from error

    return True


async def _async_start_menu_scan(hass: HomeAssistant, call) -> None:
    """Start a technical-menu scan in the background for the chosen device."""
    first_id = call.data[ATTR_FIRST_ID]
    last_id = call.data[ATTR_LAST_ID]
    if last_id < first_id:
        first_id, last_id = last_id, first_id

    entry_ids: list[str] = []
    device_id = call.data.get(ATTR_DEVICE_ID)
    if device_id:
        device_entry = dr.async_get(hass).async_get(device_id)
        if device_entry is not None:
            entry_ids = list(device_entry.config_entries)
    else:
        entry_ids = [entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)]

    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            continue
        entry_data = hass.data.get(DOMAIN, {}).get(entry.unique_id)
        if not entry_data:
            continue
        device = entry_data[COORDINATOR].device
        if device.system_type != SystemType.GALEVO:
            continue
        hass.async_create_background_task(
            _async_run_menu_scan(hass, entry.unique_id, device, first_id, last_id),
            f"{DOMAIN} menu scan",
        )


async def _async_run_menu_scan(
    hass: HomeAssistant, unique_id: str, device, first_id: int, last_id: int
) -> None:
    """Run the scan, store the result and tell the user where to find it."""
    from homeassistant.components import persistent_notification

    notification_id = f"{DOMAIN}_menu_scan"
    persistent_notification.async_create(
        hass,
        f"Scanning technical-menu items {first_id}-{last_id}. "
        "This can take up to a few minutes.",
        title="Ariston Nimbus menu scan",
        notification_id=notification_id,
    )
    try:
        result = await async_scan_menu_items(device.api, device.gw, first_id, last_id)
    except Exception as err:  # noqa: BLE001 - report instead of failing silently
        _LOGGER.exception("Ariston menu scan failed")
        persistent_notification.async_create(
            hass,
            f"Menu scan failed: {err}",
            title="Ariston Nimbus menu scan",
            notification_id=notification_id,
        )
        return

    if unique_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN][unique_id][MENU_SCAN_RESULT] = result

    path = hass.config.path(MENU_SCAN_FILE)

    def _write() -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

    try:
        await hass.async_add_executor_job(_write)
        saved = f"Saved to `{MENU_SCAN_FILE}` in the config folder. "
    except OSError as err:
        _LOGGER.warning("Could not write %s: %s", path, err)
        saved = ""

    status = "complete" if result["complete"] else "incomplete (request limit reached)"
    persistent_notification.async_create(
        hass,
        f"Scan {status}: found {result['items_found']} menu items "
        f"using {result['requests']} requests in {result['duration_seconds']} s. "
        f"{saved}The result is also included in Download diagnostics.",
        title="Ariston Nimbus menu scan",
        notification_id=notification_id,
    )


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.unique_id)

    return unload_ok
