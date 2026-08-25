"""Open-Meteo weather forecast provider."""

from __future__ import annotations

from datetime import date

import httpx

from mcp_tools.weather.exceptions import (
    WeatherMalformedResponseError,
    WeatherNoDataError,
    WeatherProviderError,
    WeatherProviderTimeoutError,
)
from mcp_tools.weather.geocoding.base import GeocodedLocation
from mcp_tools.weather.providers.weather_codes import weather_summary_for_code
from mcp_tools.weather.schemas import DailyForecast, WeatherForecastRequest

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoWeatherProvider:
    """Fetch daily forecasts from Open-Meteo."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._client = client

    def fetch_forecast(
        self,
        request: WeatherForecastRequest,
        location: GeocodedLocation,
    ) -> list[DailyForecast]:
        params: dict[str, str | float] = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,weathercode"
            ),
            "timezone": "auto",
        }
        try:
            if self._client is not None:
                response = self._client.get(
                    OPEN_METEO_FORECAST_URL,
                    params=params,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(OPEN_METEO_FORECAST_URL, params=params)
        except httpx.TimeoutException as exc:
            raise WeatherProviderTimeoutError("forecast request timed out") from exc
        except httpx.HTTPError as exc:
            raise WeatherProviderError("forecast request failed") from exc

        if response.status_code == 429:
            raise WeatherProviderError("forecast provider rate limited")
        if response.status_code >= 500:
            raise WeatherProviderError("forecast provider unavailable")
        if response.status_code >= 400:
            raise WeatherProviderError("forecast request rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherMalformedResponseError(
                "forecast response was not JSON"
            ) from exc

        daily = payload.get("daily")
        if not isinstance(daily, dict):
            raise WeatherMalformedResponseError("forecast response missing daily data")

        dates = daily.get("time")
        if not dates:
            raise WeatherNoDataError("forecast response contained no dates")

        forecasts: list[DailyForecast] = []
        for index, date_text in enumerate(dates):
            try:
                forecast_date = date.fromisoformat(str(date_text))
            except ValueError as exc:
                raise WeatherMalformedResponseError("invalid forecast date") from exc

            weather_code = _int_at(daily.get("weathercode"), index)
            forecasts.append(
                DailyForecast(
                    date=forecast_date,
                    temperature_max_c=_value_at(daily.get("temperature_2m_max"), index),
                    temperature_min_c=_value_at(daily.get("temperature_2m_min"), index),
                    precipitation_probability_max=_int_at(
                        daily.get("precipitation_probability_max"),
                        index,
                    ),
                    weather_code=weather_code,
                    weather_summary=weather_summary_for_code(weather_code),
                )
            )

        if not forecasts:
            raise WeatherNoDataError("forecast response contained no daily rows")

        return forecasts


def _value_at(values: object, index: int) -> float | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    return float(value)


def _int_at(values: object, index: int) -> int | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    return int(value)
