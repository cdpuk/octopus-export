"""Test octopus_export setup process."""
from homeassistant.exceptions import ConfigEntryNotReady
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.octopus_export import (
    OctopusTariffUpdateCoordinator,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.octopus_export.const import CONF_REGION, DOMAIN

# Mock config data to be used across multiple tests
MOCK_CONFIG = {
    CONF_REGION: "A",
}


async def test_setup_unload_and_reload_entry(
    hass, bypass_get_product, bypass_coordinator_refresh
):
    """Test entry setup, unload and reload."""
    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    # Set up the entry and assert that the values set during setup are where we expect
    # them to be. Because we have patched the GivEnergyUpdateCoordinator.async_get_data
    # call, no code from custom_components/bestway/api.py actually runs.
    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], OctopusTariffUpdateCoordinator
    )

    # Reload the entry and assert that the data from above is still there
    assert await async_reload_entry(hass, config_entry) is None
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], OctopusTariffUpdateCoordinator
    )

    # Unload the entry and verify that the data has been removed
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_exception(hass, error_on_get_product):
    """Ensure we get ConfigEntryNotReady when we can't get product information from the API."""

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    with pytest.raises(ConfigEntryNotReady):
        assert await async_setup_entry(hass, config_entry)
