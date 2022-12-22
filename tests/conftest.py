"""Global fixtures for octopus_export integration."""
from unittest.mock import patch

import pytest

from custom_components.octopus_export.octopus_api import OctopusProduct


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations."""
    yield


@pytest.fixture(name="bypass_get_product")
def bypass_get_product_fixture():
    """Skip calls to get product information."""
    with patch(
        "custom_components.octopus_export.octopus_api.ProductService.async_get_export_product",
        return_value=OctopusProduct(
            "AGILE-OUTGOING-19-05-13",
            "Agile Outgoing Octopus May 2019",
            {"A": "E-1R-AGILE-OUTGOING-19-05-13-A"},
        ),
    ):
        yield


@pytest.fixture(name="error_on_get_product")
def error_get_data_fixture():
    """Simulate error when retrieving product information."""
    with patch(
        "custom_components.octopus_export.octopus_api.ProductService.async_get_export_product",
        side_effect=Exception,
    ):
        yield


@pytest.fixture(name="bypass_coordinator_refresh")
def bypass_coordinator_refresh_fixture():
    """Skip calls to refresh tariff pricing."""
    with patch(
        "custom_components.octopus_export.OctopusTariffUpdateCoordinator._async_update_data",
    ):
        yield
