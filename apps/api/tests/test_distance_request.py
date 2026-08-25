"""Tests for distance request construction from trip requirements."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.domain.trip_request import TripRequest
from app.tools.distance_request import build_distance_matrix_request
from mcp_tools.distance.exceptions import DistanceValidationError
from mcp_tools.distance.schemas import TravelMode

from tests.fakes.distance_providers import FakeLocationResolver


def test_build_distance_request_from_trip_requirements() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    request = build_distance_matrix_request(trip_request, FakeLocationResolver())

    assert request.origins[0].name == "Mumbai"
    assert request.destinations[0].name == "Dubai"
    assert request.travel_mode is TravelMode.DRIVING


def test_build_distance_request_requires_departure_city() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city=None,
    )

    with pytest.raises(DistanceValidationError):
        build_distance_matrix_request(trip_request, FakeLocationResolver())


def test_build_distance_request_requires_destination() -> None:
    trip_request = TripRequest(
        destination=None,
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    with pytest.raises(DistanceValidationError):
        build_distance_matrix_request(trip_request, FakeLocationResolver())
