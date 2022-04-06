"""Home Assistant entity descriptions."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OctopusTariffUpdateCoordinator
from .const import CONF_REGION, DOMAIN
from .octopus_api import DNO_REGIONS


class OctopusAgileTariffEntity(CoordinatorEntity[OctopusTariffUpdateCoordinator]):
    """An entity associated with a "tariff" device."""

    def __init__(
        self, coordinator: OctopusTariffUpdateCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Tariff device information for the entity."""

        region_code = self.config_entry.data[CONF_REGION]
        region_name = DNO_REGIONS[region_code]

        return DeviceInfo(
            identifiers={(DOMAIN, f"agile-export-{region_code}")},
            name="Octopus Agile Tariff",
            model=region_name,
            manufacturer="Octopus Energy",
        )
