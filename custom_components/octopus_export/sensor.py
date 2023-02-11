"""Home Assistant sensor descriptions."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import Enum
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_MONETARY
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.typing import StateType

from . import OctopusTariffUpdateCoordinator
from .const import CONF_REGION, DOMAIN
from .entity import OctopusAgileTariffEntity
from .octopus_api import get_start_of_current_interval

_LOGGER: logging.Logger = logging.getLogger(__package__)


class Icon(str, Enum):
    """Icon styles."""

    CASH = "mdi:cash"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator: OctopusTariffUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    async_add_entities(
        [
            CurrentRateSensor(coordinator, config_entry),
        ]
    )


class CurrentRateSensor(OctopusAgileTariffEntity, SensorEntity):
    """Provides the current agile tariff rate."""

    _cancel_scheduled_update: CALLBACK_TYPE | None = None

    def __init__(
        self,
        coordinator: OctopusTariffUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self.entity_description = SensorEntityDescription(
            key="current_rates",
            name="Agile Export Rate",
            icon=Icon.CASH,
            device_class=DEVICE_CLASS_MONETARY,
            native_unit_of_measurement="£/kWh",
        )
        region_code = self.config_entry.data[CONF_REGION]
        self._attr_unique_id = f"export-{region_code}_{self.entity_description.key}"
        self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to hass."""
        await super().async_added_to_hass()
        await self._async_half_hourly_update(datetime.utcnow())

    async def async_will_remove_from_hass(self) -> None:
        """Run when the entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        if self._cancel_scheduled_update is not None:
            self._cancel_scheduled_update()

    @property
    def native_value(self) -> StateType:
        """Return the current tariff rate."""
        if self.coordinator.rates is None:
            return None

        interval_start = get_start_of_current_interval()
        return self.coordinator.rates[interval_start.strftime("%Y-%m-%dT%H:%M:%SZ")]

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Extra state attributes for the sensor."""
        if self.coordinator.rates is None:
            return None

        return {
            "rates_today": self.coordinator.rates_today,
            "rates_tomorrow": self.coordinator.rates_tomorrow,
            "current_slot": get_start_of_current_interval()
            .astimezone()
            .strftime("%H:%M"),
        }

    async def _async_half_hourly_update(self, now: datetime) -> None:
        """Trigger a refresh of the sensor, and schedule the next refresh when prices change again."""
        self.async_schedule_update_ha_state()

        # Get the timestamp of the half hour period that just began
        interval_start = get_start_of_current_interval()

        # Schedule the next update
        next_time = interval_start + timedelta(minutes=30)
        self._cancel_scheduled_update = async_track_point_in_utc_time(
            self.hass,
            self._async_half_hourly_update,
            next_time,
        )
        _LOGGER.debug("Scheduled next update for %s UTC", next_time)
