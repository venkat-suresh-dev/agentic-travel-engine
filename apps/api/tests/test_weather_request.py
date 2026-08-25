"""Tests for weather request construction from trip requirements."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.domain.trip_request import TripRequest
from app.tools.weather_request import build_weather_request, resolve_forecast_window
from mcp_tools.weather.exceptions import WeatherValidationError


def test_build_weather_request_uses_destination() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    request = build_weather_request(trip_request)

    assert request.location == "Dubai"
    assert request.end_date >= request.start_date


def test_build_weather_request_requires_destination() -> None:
    trip_request = TripRequest(
        destination=None,
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    with pytest.raises(WeatherValidationError):
        build_weather_request(trip_request)


def test_resolve_forecast_window_from_start_and_duration() -> None:
    start = date(2026, 12, 1)
    trip_request = TripRequest(
        destination="Dubai",
        start_date=start,
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        departure_city="Mumbai",
    )

    window_start, window_end = resolve_forecast_window(trip_request)

    assert window_start == start
    assert window_end == start + timedelta(days=4)
