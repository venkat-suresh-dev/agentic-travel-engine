"""Build weather requests from validated trip requirements."""

from __future__ import annotations

from datetime import date, timedelta

from mcp_tools.weather.exceptions import WeatherValidationError
from mcp_tools.weather.schemas import WeatherForecastRequest

from app.domain.trip_request import TripRequest


def resolve_forecast_window(trip_request: TripRequest) -> tuple[date, date]:
    """Derive a forecast date window from validated trip schedule fields."""
    today = date.today()
    if trip_request.start_date and trip_request.end_date:
        return trip_request.start_date, trip_request.end_date
    if trip_request.start_date and trip_request.duration_days:
        end_date = trip_request.start_date + timedelta(
            days=trip_request.duration_days - 1,
        )
        return trip_request.start_date, end_date
    if trip_request.start_date:
        return trip_request.start_date, trip_request.start_date
    if trip_request.duration_days:
        end_date = today + timedelta(days=trip_request.duration_days - 1)
        return today, end_date
    return today, today


def build_weather_request(trip_request: TripRequest) -> WeatherForecastRequest:
    """Create a weather tool request from validated trip requirements."""
    if not trip_request.destination:
        raise WeatherValidationError("destination is required for weather lookup")

    start_date, end_date = resolve_forecast_window(trip_request)
    return WeatherForecastRequest(
        location=trip_request.destination,
        start_date=start_date,
        end_date=end_date,
    )
