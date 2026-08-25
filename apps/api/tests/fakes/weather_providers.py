"""Fake weather providers for API integration tests."""

from __future__ import annotations

from mcp_tools.weather.geocoding.base import GeocodedLocation
from mcp_tools.weather.schemas import DailyForecast, WeatherForecastRequest


class FakeGeocodingProvider:
    def geocode(self, location: str) -> GeocodedLocation:
        return GeocodedLocation(
            name=location.title(),
            latitude=25.2048,
            longitude=55.2708,
            country="United Arab Emirates",
        )


class FakeWeatherProvider:
    def fetch_forecast(
        self,
        request: WeatherForecastRequest,
        location: GeocodedLocation,
    ) -> list[DailyForecast]:
        return [
            DailyForecast(
                date=request.start_date,
                temperature_max_c=34.0,
                temperature_min_c=24.0,
                precipitation_probability_max=10,
                weather_summary="Clear sky",
                weather_code=0,
            )
        ]
