"""Geoapify Places provider for restaurants and attractions."""

from __future__ import annotations

from collections.abc import Mapping

import httpx

from mcp_tools.places.exceptions import (
    PlacesMalformedResponseError,
    PlacesProviderError,
    PlacesProviderTimeoutError,
    PlacesRateLimitError,
)
from mcp_tools.places.providers.geoapify_normalize import (
    parse_geoapify_attraction_places,
    parse_geoapify_restaurant_places,
)
from mcp_tools.places.schemas import (
    AttractionPlace,
    AttractionSearchRequest,
    RestaurantPlace,
    RestaurantSearchRequest,
)

DEFAULT_GEOAPIFY_BASE_URL = "https://api.geoapify.com"
PLACES_PATH = "/v2/places"

_RESTAURANT_CATEGORIES = "catering.restaurant"
_ATTRACTION_CATEGORIES = "tourism"


class GeoapifyPlacesProvider:
    """Search restaurants and attractions via Geoapify Places API."""

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

    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> list[RestaurantPlace]:
        params: dict[str, str | int] = {
            "categories": _RESTAURANT_CATEGORIES,
            "filter": (
                f"circle:{request.location.longitude},{request.location.latitude},"
                f"{request.radius_meters}"
            ),
            "bias": (
                f"proximity:{request.location.longitude},{request.location.latitude}"
            ),
            "limit": request.max_results,
            "apiKey": self._api_key,
        }
        payload = self._get(PLACES_PATH, params)
        return parse_geoapify_restaurant_places(payload)

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> list[AttractionPlace]:
        params: dict[str, str | int] = {
            "categories": _ATTRACTION_CATEGORIES,
            "filter": (
                f"circle:{request.location.longitude},{request.location.latitude},"
                f"{request.radius_meters}"
            ),
            "bias": (
                f"proximity:{request.location.longitude},{request.location.latitude}"
            ),
            "limit": request.max_results,
            "apiKey": self._api_key,
        }
        payload = self._get(PLACES_PATH, params)
        return parse_geoapify_attraction_places(payload)

    def _get(
        self, path: str, params: Mapping[str, str | int | float | bool]
    ) -> dict[str, object]:
        url = f"{self._base_url}{path}"
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
            raise PlacesProviderTimeoutError("places search request timed out") from exc
        except httpx.HTTPError as exc:
            raise PlacesProviderError("places search request failed") from exc

        if response.status_code == 429:
            raise PlacesRateLimitError("places provider rate limited")
        if response.status_code >= 500:
            raise PlacesProviderError("places provider unavailable")
        if response.status_code >= 400:
            raise PlacesProviderError("places search request rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise PlacesMalformedResponseError(
                "places search response was not JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise PlacesMalformedResponseError("places response was not an object")
        return payload
