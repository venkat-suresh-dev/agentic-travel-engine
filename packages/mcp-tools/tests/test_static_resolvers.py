"""Tests for static airport and city resolvers."""

from __future__ import annotations

import pytest

from mcp_tools.flights.airports.static import StaticAirportCodeResolver
from mcp_tools.flights.exceptions import FlightValidationError
from mcp_tools.hotels.locations.static import StaticCityCodeResolver


def test_static_airport_resolver() -> None:
    resolver = StaticAirportCodeResolver()
    assert resolver.resolve("Mumbai") == "BOM"
    assert resolver.resolve("Dubai") == "DXB"
    assert resolver.resolve("dxb") == "DXB"


def test_static_city_resolver() -> None:
    resolver = StaticCityCodeResolver()
    assert resolver.resolve("Mumbai") == "BOM"
    assert resolver.resolve("Dubai") == "DXB"


def test_static_airport_resolver_unknown() -> None:
    resolver = StaticAirportCodeResolver()
    with pytest.raises(FlightValidationError):
        resolver.resolve("Unknownville")
