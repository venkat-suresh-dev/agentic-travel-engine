"""Tests for hotel request construction from trip requirements."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.domain.trip_request import TripRequest
from app.tools.hotels_request import (
    build_hotel_search_request,
    resolve_hotel_stay_window,
)
from mcp_tools.hotels.exceptions import HotelValidationError

from tests.fakes.hotels_providers import FakeCityCodeResolver


def test_build_single_room_hotel_request() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    request = build_hotel_search_request(trip_request, FakeCityCodeResolver())

    assert request.location == "Dubai"
    assert request.city_code == "DXB"
    assert request.travelers == 2
    assert request.rooms == 1
    assert request.currency == "INR"


def test_build_multi_room_hotel_request() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 6),
        travelers=4,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    request = build_hotel_search_request(trip_request, FakeCityCodeResolver())

    assert request.check_in == date(2026, 12, 1)
    assert request.check_out == date(2026, 12, 6)
    assert request.rooms == 2


def test_resolve_hotel_stay_window_from_duration() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        start_date=date(2026, 12, 1),
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    check_in, check_out = resolve_hotel_stay_window(trip_request)

    assert check_in == date(2026, 12, 1)
    assert check_out == date(2026, 12, 6)


def test_build_hotel_request_requires_destination() -> None:
    trip_request = TripRequest(
        destination=None,
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    with pytest.raises(HotelValidationError):
        build_hotel_search_request(trip_request, FakeCityCodeResolver())


def test_invalid_traveler_count_rejected() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=None,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    with pytest.raises(HotelValidationError):
        build_hotel_search_request(trip_request, FakeCityCodeResolver())
