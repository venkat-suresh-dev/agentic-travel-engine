"""Fake flight tool wiring for API tests."""

from __future__ import annotations

import pytest
from app.tools.flights import FlightTool
from mcp_tools.flights.cache import FlightCache
from mcp_tools.flights.service import FlightService

from tests.fakes.flights_providers import FakeAirportCodeResolver, FakeFlightProvider


@pytest.fixture
def fake_airport_resolver() -> FakeAirportCodeResolver:
    return FakeAirportCodeResolver()


@pytest.fixture
def fake_flight_service() -> FlightService:
    return FlightService(
        flight_provider=FakeFlightProvider(),
        cache=FlightCache(),
    )


@pytest.fixture
def fake_flight_tool(fake_flight_service: FlightService) -> FlightTool:
    return FlightTool(fake_flight_service)
