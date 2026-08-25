"""Tests for flight request construction from trip requirements."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.domain.trip_request import TripRequest
from app.tools.flights_request import build_flight_search_request
from mcp_tools.flights.exceptions import FlightValidationError

from tests.fakes.flights_providers import FakeAirportCodeResolver


def test_build_one_way_flight_request() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    request = build_flight_search_request(trip_request, FakeAirportCodeResolver())

    assert request.origin == "BOM"
    assert request.destination == "DXB"
    assert request.travelers == 2
    assert request.currency == "INR"
    assert request.return_date is None


def test_build_round_trip_flight_request_when_end_date_present() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 6),
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    request = build_flight_search_request(trip_request, FakeAirportCodeResolver())

    assert request.departure_date == date(2026, 12, 1)
    assert request.return_date == date(2026, 12, 6)


def test_build_flight_request_requires_departure_city() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city=None,
    )

    with pytest.raises(FlightValidationError):
        build_flight_search_request(trip_request, FakeAirportCodeResolver())


def test_invalid_traveler_count_rejected() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=None,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    with pytest.raises(FlightValidationError):
        build_flight_search_request(trip_request, FakeAirportCodeResolver())
