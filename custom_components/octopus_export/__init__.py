"""The Octopus Agile integration."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_REGION, DOMAIN, LOGGER
from .octopus_api import AgileRates, AgileTariff, ProductService

_PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octopus Agile from a config entry."""

    session = async_get_clientsession(hass)
    product_svc = ProductService(session)

    try:
        product = await product_svc.async_get_export_product()

        product_code = product.code
        region_code = entry.data.get(CONF_REGION)
        tariff_code = product.tariff_codes[region_code]
        tariff = AgileTariff(session, product_code, tariff_code)

        coordinator = OctopusTariffUpdateCoordinator(hass, tariff)
        await coordinator.async_config_entry_first_refresh()

        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
        hass.config_entries.async_setup_platforms(entry, _PLATFORMS)

        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        return True
    except Exception as ex:  # pylint: disable=broad-except
        raise ConfigEntryNotReady from ex


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(
        entry, _PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class OctopusTariffUpdateCoordinator(DataUpdateCoordinator[AgileRates]):
    """Update coordinator that enables efficient batched updates to all entities associated with an inverter."""

    rates: AgileRates = {}

    def __init__(self, hass: HomeAssistant, tariff: AgileTariff) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name="Agile Tariff",
            update_interval=timedelta(seconds=900),
        )
        self.tariff = tariff

    async def _async_update_data(self) -> AgileRates:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(10):
                raw_data = await self.tariff.fetch_data()
                self.rates = dict(sorted(raw_data.items()))
                return self.rates
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    @property
    def rates_today(self) -> AgileRates:
        """
        Get today's rates in the current timezone.

        The dictionary keys reflect the start of the agile pricing slot, e.g. '18:30'.
        """
        today = datetime.now().date()
        return {
            self._local_time_from_utc_timestamp(key): value
            for (key, value) in filter(
                lambda entry: self._is_date(entry[0], today),
                self.rates.items(),
            )
        }

    @property
    def rates_tomorrow(self) -> AgileRates:
        """
        Get tomorrow's rates in the current timezone.

        The dictionary keys reflect the start of the agile pricing slot, e.g. '18:30'.
        """
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        return {
            self._local_time_from_utc_timestamp(key): value
            for (key, value) in filter(
                lambda entry: self._is_date(entry[0], tomorrow),
                self.rates.items(),
            )
        }

    def _is_date(self, timestamp: str, date_to_match: date) -> bool:
        """Check whether the timestamp occurs on the date to be matched."""
        parsed_date = (
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            .astimezone()
            .date()
        )
        return parsed_date == date_to_match

    def _local_time_from_utc_timestamp(self, timestamp: str) -> str:
        """Get the local HH:mm representation of a UTC timestamp."""
        return (
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            .astimezone()
            .strftime("%H:%M")
        )
