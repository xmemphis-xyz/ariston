"""Support for Ariston Boost switches."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import ARISTON_SWITCH_TYPES, DOMAIN, Ariston BoostSwitchEntityDescription
from .coordinator import DeviceDataUpdateCoordinator
from .entity import Ariston BoostEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Ariston Boost switches from config entry."""
    ariston_switches: list[Ariston BoostSwitch] = []
    for description in ARISTON_SWITCH_TYPES:
        coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][entry.unique_id][
            description.coordinator
        ]
        if (
            coordinator
            and coordinator.device
            and coordinator.device.are_device_features_available(
                description.device_features,
                description.system_types,
                description.whe_types,
            )
        ):
            ariston_switches.append(
                Ariston BoostSwitch(
                    coordinator,
                    description,
                )
            )

    async_add_entities(ariston_switches)


class Ariston BoostSwitch(Ariston BoostEntity, SwitchEntity):
    """Base class for specific ariston switches."""

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: Ariston BoostSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description)

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.entity_description.get_is_on(self)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.entity_description.set_value(self, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        await self.entity_description.set_value(self, False)
        self.async_write_ha_state()
