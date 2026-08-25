"""Request builder tests for restaurant search."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.domain.trip_request import TripRequest
from app.tools.restaurants_request import build_restaurant_search_request
from mcp_tools.places.exceptions import PlacesValidationError
from mcp_tools.places.schemas import RestaurantSearchRequest

from tests.fakes.distance_providers import FakeLocationResolver


def test_build_restaurant_search_request_from_trip_request() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )
    request = build_restaurant_search_request(trip_request, FakeLocationResolver())
    assert isinstance(request, RestaurantSearchRequest)
    assert request.location.name == "Dubai"
    assert request.location.latitude == pytest.approx(25.2048)
    assert request.location.longitude == pytest.approx(55.2708)


def test_build_restaurant_search_request_requires_destination() -> None:
    trip_request = TripRequest(
        destination=None,
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )
    with pytest.raises(PlacesValidationError):
        build_restaurant_search_request(trip_request, FakeLocationResolver())
