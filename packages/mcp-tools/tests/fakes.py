"""Fake weather providers for offline tests."""

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
    def __init__(
        self,
        *,
        should_fail: bool = False,
        malformed: bool = False,
        forecasts: list[DailyForecast] | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.malformed = malformed
        self.forecasts = forecasts

    def fetch_forecast(
        self,
        request: WeatherForecastRequest,
        location: GeocodedLocation,
    ) -> list[DailyForecast]:
        if self.should_fail:
            from mcp_tools.weather.exceptions import WeatherProviderError

            raise WeatherProviderError("simulated provider failure")
        if self.malformed:
            from mcp_tools.weather.exceptions import WeatherMalformedResponseError

            raise WeatherMalformedResponseError("simulated malformed response")
        if self.forecasts is not None:
            return self.forecasts
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


class FailingGeocodingProvider:
    def geocode(self, location: str) -> GeocodedLocation:
        from mcp_tools.weather.exceptions import GeocodingError

        raise GeocodingError(f"location not found: {location}")
