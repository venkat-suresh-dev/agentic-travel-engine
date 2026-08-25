"""Google Places API (New) provider."""

from __future__ import annotations

import httpx

from mcp_tools.places.exceptions import (
    PlacesMalformedResponseError,
    PlacesProviderError,
    PlacesProviderTimeoutError,
    PlacesRateLimitError,
)
from mcp_tools.places.providers.google_field_masks import (
    ATTRACTION_SEARCH_FIELD_MASK,
    RESTAURANT_SEARCH_FIELD_MASK,
)
from mcp_tools.places.providers.normalize import (
    parse_google_attraction_places,
    parse_google_restaurant_places,
)
from mcp_tools.places.schemas import (
    AttractionPlace,
    AttractionSearchRequest,
    RestaurantCuisine,
    RestaurantPlace,
    RestaurantPriceLevel,
    RestaurantSearchRequest,
)

DEFAULT_GOOGLE_PLACES_BASE_URL = "https://places.googleapis.com"
TEXT_SEARCH_PATH = "/v1/places:searchText"
NEARBY_SEARCH_PATH = "/v1/places:searchNearby"

_GOOGLE_PRICE_LEVEL_MAP: dict[RestaurantPriceLevel, str] = {
    RestaurantPriceLevel.INEXPENSIVE: "PRICE_LEVEL_INEXPENSIVE",
    RestaurantPriceLevel.MODERATE: "PRICE_LEVEL_MODERATE",
    RestaurantPriceLevel.EXPENSIVE: "PRICE_LEVEL_EXPENSIVE",
    RestaurantPriceLevel.VERY_EXPENSIVE: "PRICE_LEVEL_VERY_EXPENSIVE",
}

_CUISINE_TEXT_QUERY: dict[RestaurantCuisine, str] = {
    RestaurantCuisine.ITALIAN: "italian restaurant",
    RestaurantCuisine.INDIAN: "indian restaurant",
    RestaurantCuisine.CHINESE: "chinese restaurant",
    RestaurantCuisine.JAPANESE: "japanese restaurant",
    RestaurantCuisine.MEXICAN: "mexican restaurant",
    RestaurantCuisine.FRENCH: "french restaurant",
    RestaurantCuisine.AMERICAN: "american restaurant",
    RestaurantCuisine.MEDITERRANEAN: "mediterranean restaurant",
    RestaurantCuisine.THAI: "thai restaurant",
    RestaurantCuisine.MIDDLE_EASTERN: "middle eastern restaurant",
}


class GooglePlacesProvider:
    """Search restaurants and attractions via Google Places API (New)."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_GOOGLE_PLACES_BASE_URL,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    @property
    def restaurant_field_mask(self) -> str:
        return RESTAURANT_SEARCH_FIELD_MASK

    @property
    def attraction_field_mask(self) -> str:
        return ATTRACTION_SEARCH_FIELD_MASK

    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> list[RestaurantPlace]:
        body = self._build_restaurant_text_search_body(request)
        payload = self._post(
            path=TEXT_SEARCH_PATH,
            field_mask=self.restaurant_field_mask,
            body=body,
            language_code=request.language_code,
            region_code=request.region_code,
        )
        return parse_google_restaurant_places(payload)

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> list[AttractionPlace]:
        body = self._build_attraction_nearby_search_body(request)
        payload = self._post(
            path=NEARBY_SEARCH_PATH,
            field_mask=self.attraction_field_mask,
            body=body,
            language_code=request.language_code,
            region_code=request.region_code,
        )
        return parse_google_attraction_places(payload)

    def _build_restaurant_text_search_body(
        self,
        request: RestaurantSearchRequest,
    ) -> dict[str, object]:
        text_query = "restaurant"
        if request.cuisine is not None:
            text_query = _CUISINE_TEXT_QUERY[request.cuisine]
        body: dict[str, object] = {
            "textQuery": text_query,
            "includedType": "restaurant",
            "maxResultCount": request.max_results,
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": request.location.latitude,
                        "longitude": request.location.longitude,
                    },
                    "radius": float(request.radius_meters),
                }
            },
        }
        if request.price_levels:
            body["priceLevels"] = [
                _GOOGLE_PRICE_LEVEL_MAP[level] for level in request.price_levels
            ]
        return body

    def _build_attraction_nearby_search_body(
        self,
        request: AttractionSearchRequest,
    ) -> dict[str, object]:
        return {
            "includedTypes": [category.value for category in request.categories],
            "maxResultCount": request.max_results,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": request.location.latitude,
                        "longitude": request.location.longitude,
                    },
                    "radius": float(request.radius_meters),
                }
            },
            "rankPreference": "POPULARITY",
        }

    def _post(
        self,
        *,
        path: str,
        field_mask: str,
        body: dict[str, object],
        language_code: str | None,
        region_code: str | None,
    ) -> dict[str, object]:
        if "*" in field_mask:
            raise PlacesMalformedResponseError("wildcard field masks are not allowed")

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": field_mask,
        }
        if language_code:
            body = {**body, "languageCode": language_code}
        if region_code:
            body = {**body, "regionCode": region_code}

        url = f"{self._base_url}{path}"
        try:
            if self._client is not None:
                response = self._client.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client() as client:
                    response = client.post(
                        url,
                        json=body,
                        headers=headers,
                        timeout=self._timeout_seconds,
                    )
        except httpx.TimeoutException as exc:
            raise PlacesProviderTimeoutError("google places request timed out") from exc
        except httpx.HTTPError as exc:
            raise PlacesProviderError("google places request failed") from exc

        if response.status_code == 429:
            raise PlacesRateLimitError("google places rate limit exceeded")
        if response.status_code >= 400:
            raise PlacesProviderError(
                f"google places request failed with status {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise PlacesMalformedResponseError(
                "google places response was not valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise PlacesMalformedResponseError(
                "google places response was not an object"
            )
        return payload
