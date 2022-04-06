"""Config flow for GivEnergy integration."""
from __future__ import annotations

from typing import Any

import async_timeout
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import CONF_REGION, DOMAIN, LOGGER
from .octopus_api import AgileTariff, ProductService

DNO_REGIONS = [
    selector.SelectOptionDict(value="A", label="A/10: Eastern England"),
    selector.SelectOptionDict(value="B", label="B/11: East Midlands"),
    selector.SelectOptionDict(value="C", label="C/12: London"),
    selector.SelectOptionDict(value="D", label="D/13: Merseyside and Northern Wales"),
    selector.SelectOptionDict(value="E", label="E/14: West Midlands"),
    selector.SelectOptionDict(value="F", label="F/15: North Eastern England"),
    selector.SelectOptionDict(value="G", label="G/16: North Western England"),
    selector.SelectOptionDict(value="H", label="H/20: Southern England"),
    selector.SelectOptionDict(value="J", label="J/19: South Eastern England"),
    selector.SelectOptionDict(value="K", label="K/21: Southern Wales"),
    selector.SelectOptionDict(value="L", label="L/22: South Western England"),
    selector.SelectOptionDict(value="M", label="M/23: Yorkshire"),
    selector.SelectOptionDict(value="N", label="N/18: Southern Scotland"),
    selector.SelectOptionDict(value="P", label="P/17: Northern Scotland"),
]

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION): selector.SelectSelector(
            selector.SelectSelectorConfig(options=DNO_REGIONS),
        )
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        session = async_get_clientsession(hass)
        product_svc = ProductService(session)
        product = await product_svc.async_get_export_product()

        product_code = product.code
        region_code = data[CONF_REGION]
        tariff_code = product.tariff_codes[region_code]
        tariff = AgileTariff(session, product_code, tariff_code)
        async with async_timeout.timeout(10):
            await tariff.fetch_data()

        return {CONF_REGION: region_code}
    except Exception:  # pylint: disable=broad-except
        raise CannotConnect from Exception


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Octopus Agile."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            config_data = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(
                title="Agile Export Tariff", data=config_data
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
