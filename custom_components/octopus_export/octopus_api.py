"""Octopus Agile API."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from aiohttp import ClientSession
import async_timeout

_HEADERS = {"Content-type": "application/json; charset=UTF-8"}
_TIMEOUT = 10

AgileRates = dict[str, float]

DNO_REGIONS = {
    "A": "Eastern England",
    "B": "East Midlands",
    "C": "London",
    "D": "Merseyside and Northern Wales",
    "E": "West Midlands",
    "F": "North Eastern England",
    "G": "North Western England",
    "H": "Southern England",
    "J": "South Eastern England",
    "K": "Southern Wales",
    "L": "South Western England",
    "M": "Yorkshire",
    "N": "Southern Scotland",
    "P": "Northern Scotland",
}


@dataclass
class OctopusProduct:
    """An Octopus Energy product."""

    code: str
    name: str
    tariff_codes: dict[str, str]


class JSONProduct(TypedDict):
    """JSON product representation."""

    code: str
    direction: Literal["IMPORT", "EXPORT"]
    display_name: str


class JSONProductsRespone(TypedDict):
    """JSON root element for https://api.octopus.energy//v1/products/."""

    results: list[JSONProduct]


class JSONDirectDebitMonthly(TypedDict):
    """JSON direct debit rates."""

    code: str


class JSONElectricityTariff(TypedDict):
    """JSON electricity tariff rates."""

    direct_debit_monthly: JSONDirectDebitMonthly


class JSONProductResponse(TypedDict):
    """JSON root element for https://api.octopus.energy/v1/products/<id>/."""

    single_register_electricity_tariffs: dict[str, JSONElectricityTariff]


class ProductDiscoveryException(Exception):
    """An error locating product or tariff information."""


class ProductService:
    """Provides access to product and tariff metadata."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the product data service."""
        self._session = session

    async def async_get_export_product(self) -> OctopusProduct:
        """Get the string that identifies the currently available Agile Export tariff."""
        product_data: JSONProductsRespone = await _async_call_api(
            self._session, "https://api.octopus.energy/v1/products/?is_variable=true"
        )

        export_product_data = next(
            filter(
                lambda product: product["direction"] == "EXPORT",
                product_data["results"],
            ),
            None,
        )

        if export_product_data is None:
            raise ProductDiscoveryException()

        product_code = export_product_data["code"]
        tariff_data: JSONProductResponse = await _async_call_api(
            self._session,
            f"https://api.octopus.energy/v1/products/{product_code}/",
        )

        electricity_tariffs = tariff_data["single_register_electricity_tariffs"]
        tariffs: dict[str, str] = {}
        for region_code in DNO_REGIONS:
            tariffs[region_code] = electricity_tariffs[f"_{region_code}"][
                "direct_debit_monthly"
            ]["code"]

        return OctopusProduct(
            export_product_data["code"], export_product_data["display_name"], tariffs
        )


class AgileTariff:
    """
    Represents an Octopus Energy Agile tariff.

    A tariff represents the rates assigned to a product within a given DNO region.
    """

    def __init__(self, session: ClientSession, product: str, tariff: str) -> None:
        """Initialize the tariff for fething data."""
        self._session = session
        self.product = product
        self.tariff = tariff

    async def fetch_data(self) -> AgileRates:
        """Fetch data from the Octopus API."""
        api_data = await _async_call_api(
            self._session,
            f"https://api.octopus.energy/v1/products/{self.product}"
            + f"/electricity-tariffs/{self.tariff}/standard-unit-rates",
        )
        return {
            entry["valid_from"]: round(entry["value_inc_vat"] / 100, 4)
            for entry in api_data["results"]
        }


async def _async_call_api(session: ClientSession, url: str) -> Any:
    """Make an API call to the specified URL, returning the response as a JSON object."""
    async with async_timeout.timeout(_TIMEOUT):
        response = await session.get(url, headers=_HEADERS)
        response.raise_for_status()
        return await response.json()


def get_start_of_current_interval() -> datetime:
    """Get the UTC timestamp of the start of the current half hour billing period."""
    now = datetime.now(timezone.utc)
    minutes_past_hour = 0 if now.minute < 30 else 30
    return now.replace(minute=minutes_past_hour, second=0, microsecond=0)
