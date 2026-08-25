"""Geoapify geocoding provider."""

from __future__ import annotations

import httpx

from mcp_tools.weather.exceptions import (
    WeatherMalformedResponseError,
    WeatherProviderError,
    WeatherProviderTimeoutError,
)
from mcp_tools.weather.geocoding.base import GeocodedLocation

DEFAULT_GEOAPIFY_BASE_URL = "https://api.geoapify.com"
GEOCODE_PATH = "/v1/geocode/search"


class GeoapifyGeocodingProvider:
    """Resolve human-readable locations via Geoapify Geocoding API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_GEOAPIFY_BASE_URL,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Geoapify API key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def geocode(self, location: str) -> GeocodedLocation:
        params: dict[str, str | int] = {
            "text": location,
            "apiKey": self._api_key,
            "limit": 1,
        }
        url = f"{self._base_url}{GEOCODE_PATH}"

        try:
            if self._client is not None:
                response = self._client.get(
                    url,
                    params=params,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise WeatherProviderTimeoutError("geocoding request timed out") from exc
        except httpx.HTTPError as exc:
            raise WeatherProviderError("geocoding request failed") from exc

        if response.status_code >= 400:
            raise WeatherProviderError("geocoding request rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherMalformedResponseError(
                "geocoding response was not JSON"
            ) from exc

        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list) or not features:
            raise WeatherMalformedResponseError(
                "geocoding response contained no results"
            )

        feature = features[0]
        if not isinstance(feature, dict):
            raise WeatherMalformedResponseError("geocoding feature was not an object")

        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            raise WeatherMalformedResponseError("geocoding feature missing fields")

        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise WeatherMalformedResponseError("geocoding feature missing coordinates")

        name = str(properties.get("formatted") or properties.get("city") or location)
        country = properties.get("country")
        return GeocodedLocation(
            name=name,
            latitude=float(coordinates[1]),
            longitude=float(coordinates[0]),
            country=str(country) if isinstance(country, str) else None,
        )
