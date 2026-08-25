"""Open-Meteo geocoding provider."""

from __future__ import annotations

import httpx

from mcp_tools.weather.exceptions import (
    GeocodingError,
    WeatherMalformedResponseError,
    WeatherProviderError,
    WeatherProviderTimeoutError,
)
from mcp_tools.weather.geocoding.base import GeocodedLocation

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


class OpenMeteoGeocodingProvider:
    """Resolve locations using the Open-Meteo geocoding API."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._client = client

    def geocode(self, location: str) -> GeocodedLocation:
        params: dict[str, str | int] = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        try:
            if self._client is not None:
                response = self._client.get(
                    OPEN_METEO_GEOCODING_URL,
                    params=params,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(OPEN_METEO_GEOCODING_URL, params=params)
        except httpx.TimeoutException as exc:
            raise WeatherProviderTimeoutError("geocoding request timed out") from exc
        except httpx.HTTPError as exc:
            raise WeatherProviderError("geocoding request failed") from exc

        if response.status_code == 429:
            raise WeatherProviderError("geocoding provider rate limited")
        if response.status_code >= 500:
            raise WeatherProviderError("geocoding provider unavailable")
        if response.status_code >= 400:
            raise WeatherProviderError("geocoding request rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherMalformedResponseError(
                "geocoding response was not JSON"
            ) from exc

        results = payload.get("results")
        if not results:
            raise GeocodingError(f"location not found: {location}")

        first = results[0]
        try:
            return GeocodedLocation(
                name=str(first["name"]),
                latitude=float(first["latitude"]),
                longitude=float(first["longitude"]),
                country=first.get("country"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WeatherMalformedResponseError(
                "geocoding response missing required fields"
            ) from exc
