"""Request builder tests for attraction search."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.domain.trip_request import TripRequest
from app.tools.attractions_request import build_attraction_search_request
from mcp_tools.places.exceptions import PlacesValidationError
from mcp_tools.places.schemas import AttractionCategory, AttractionSearchRequest

from tests.fakes.distance_providers import FakeLocationResolver


def test_build_attraction_search_request_from_trip_request() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )
    request = build_attraction_search_request(trip_request, FakeLocationResolver())
    assert isinstance(request, AttractionSearchRequest)
    assert request.location.name == "Dubai"
    assert request.categories == [AttractionCategory.TOURIST_ATTRACTION]


def test_build_attraction_search_request_requires_destination() -> None:
    trip_request = TripRequest(
        destination=None,
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )
    with pytest.raises(PlacesValidationError):
        build_attraction_search_request(trip_request, FakeLocationResolver())
