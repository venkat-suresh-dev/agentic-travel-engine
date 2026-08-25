"""Places MCP tool tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mcp_tools.places.cache import PlacesCache
from mcp_tools.places.exceptions import (
    PlacesMalformedResponseError,
    PlacesProviderTimeoutError,
)
from mcp_tools.places.mcp_server import create_places_mcp_server
from mcp_tools.places.providers.google_field_masks import (
    ATTRACTION_SEARCH_FIELD_MASK,
    RESTAURANT_SEARCH_FIELD_MASK,
)
from mcp_tools.places.providers.google_places import GooglePlacesProvider
from mcp_tools.places.providers.normalize import (
    parse_google_attraction_places,
    parse_google_restaurant_places,
)
from mcp_tools.places.schemas import (
    AttractionCategory,
    AttractionSearchRequest,
    PlacesDataStatus,
    RestaurantCuisine,
    RestaurantPriceLevel,
    RestaurantSearchRequest,
    SearchLocation,
)
from mcp_tools.places.service import PlacesService
from tests.fakes import FakePlacesProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"

DUBAI = SearchLocation(name="Dubai", latitude=25.2048, longitude=55.2708)


@pytest.fixture
def restaurant_request() -> RestaurantSearchRequest:
    return RestaurantSearchRequest(
        location=DUBAI,
        radius_meters=5_000,
        cuisine=RestaurantCuisine.INDIAN,
        price_levels=[RestaurantPriceLevel.MODERATE],
        max_results=5,
        language_code="en",
        region_code="AE",
    )


@pytest.fixture
def attraction_request() -> AttractionSearchRequest:
    return AttractionSearchRequest(
        location=DUBAI,
        radius_meters=5_000,
        categories=[AttractionCategory.MUSEUM, AttractionCategory.TOURIST_ATTRACTION],
        max_results=5,
        language_code="en",
        region_code="AE",
    )


def test_restaurant_request_validation(
    restaurant_request: RestaurantSearchRequest,
) -> None:
    assert restaurant_request.cuisine is RestaurantCuisine.INDIAN
    assert restaurant_request.max_results == 5


def test_attraction_request_validation(
    attraction_request: AttractionSearchRequest,
) -> None:
    assert len(attraction_request.categories) == 2
    assert attraction_request.max_results == 5


def test_invalid_radius_rejected() -> None:
    with pytest.raises(ValueError):
        RestaurantSearchRequest(location=DUBAI, radius_meters=50)


def test_invalid_max_results_rejected() -> None:
    with pytest.raises(ValueError):
        RestaurantSearchRequest(location=DUBAI, max_results=0)


def test_malformed_coordinates_rejected() -> None:
    with pytest.raises(ValueError):
        SearchLocation(name="Bad", latitude=120.0, longitude=55.0)


def test_unsupported_cuisine_rejected() -> None:
    with pytest.raises(ValueError):
        RestaurantSearchRequest.model_validate(
            {
                "location": DUBAI.model_dump(),
                "cuisine": "sushi",
            }
        )


def test_unsupported_attraction_category_rejected() -> None:
    with pytest.raises(ValueError):
        AttractionSearchRequest.model_validate(
            {
                "location": DUBAI.model_dump(),
                "categories": ["shopping_mall"],
            }
        )


def test_restaurant_fixture_normalization() -> None:
    payload = json.loads((FIXTURES_DIR / "google_places_restaurants.json").read_text())
    restaurants = parse_google_restaurant_places(payload)
    assert len(restaurants) == 1
    restaurant = restaurants[0]
    assert restaurant.place_id == "places/ChIJrestaurant1"
    assert restaurant.name == "Spice Route"
    assert restaurant.rating == 4.5
    assert restaurant.user_rating_count == 842
    assert restaurant.price_level is RestaurantPriceLevel.MODERATE
    assert restaurant.price_range is not None
    assert restaurant.opening_hours is not None
    assert restaurant.opening_hours.weekday_descriptions


def test_attraction_fixture_normalization() -> None:
    payload = json.loads((FIXTURES_DIR / "google_places_attractions.json").read_text())
    attractions = parse_google_attraction_places(payload)
    assert len(attractions) == 1
    attraction = attractions[0]
    assert attraction.primary_type == "tourist_attraction"
    assert attraction.rating == 4.8
    assert attraction.opening_hours is not None


def test_missing_optional_fields_remain_missing() -> None:
    payload = {
        "places": [
            {
                "id": "places/ChIJminimal",
                "displayName": {"text": "Minimal Place"},
                "location": {"latitude": 1.0, "longitude": 2.0},
            }
        ]
    }
    restaurant = parse_google_restaurant_places(payload)[0]
    assert restaurant.address is None
    assert restaurant.rating is None
    assert restaurant.price_level is None


def test_malformed_provider_response_rejected() -> None:
    with pytest.raises(PlacesMalformedResponseError):
        parse_google_restaurant_places({"places": "not-a-list"})


def test_restaurant_field_mask_has_no_wildcard() -> None:
    assert "*" not in RESTAURANT_SEARCH_FIELD_MASK
    assert "places.id" in RESTAURANT_SEARCH_FIELD_MASK
    assert "places.priceRange" in RESTAURANT_SEARCH_FIELD_MASK


def test_attraction_field_mask_has_no_wildcard() -> None:
    assert "*" not in ATTRACTION_SEARCH_FIELD_MASK
    assert "places.id" in ATTRACTION_SEARCH_FIELD_MASK
    assert "places.priceRange" not in ATTRACTION_SEARCH_FIELD_MASK


def test_google_provider_exposes_field_masks() -> None:
    provider = GooglePlacesProvider(api_key="test-key")
    assert provider.restaurant_field_mask == RESTAURANT_SEARCH_FIELD_MASK
    assert provider.attraction_field_mask == ATTRACTION_SEARCH_FIELD_MASK


def test_live_restaurant_response_has_provenance(
    restaurant_request: RestaurantSearchRequest,
) -> None:
    service = PlacesService(
        places_provider=FakePlacesProvider(),
        cache=PlacesCache(),
    )
    result, metadata = service.search_restaurants(restaurant_request)
    assert result.data_status is PlacesDataStatus.LIVE
    assert result.source == "google-places"
    assert result.restaurants
    assert metadata.tool_name == "search_restaurants"
    assert metadata.cache_status == "miss"


def test_live_attraction_response_has_provenance(
    attraction_request: AttractionSearchRequest,
) -> None:
    service = PlacesService(
        places_provider=FakePlacesProvider(),
        cache=PlacesCache(),
    )
    result, metadata = service.search_attractions(attraction_request)
    assert result.data_status is PlacesDataStatus.LIVE
    assert result.attractions
    assert metadata.tool_name == "search_attractions"


def test_provider_timeout_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    class FlakyProvider(FakePlacesProvider):
        def search_restaurants(self, request):  # type: ignore[no-untyped-def]
            calls["count"] += 1
            if calls["count"] == 1:
                raise PlacesProviderTimeoutError("timeout")
            return super().search_restaurants(request)

    service = PlacesService(
        places_provider=FlakyProvider(),
        cache=PlacesCache(),
        retry_backoff_seconds=0.0,
    )
    result, _metadata = service.search_restaurants(
        RestaurantSearchRequest(location=DUBAI),
    )
    assert calls["count"] == 2
    assert result.data_status is PlacesDataStatus.LIVE


def test_cached_fallback_after_provider_failure(
    restaurant_request: RestaurantSearchRequest,
) -> None:
    cache = PlacesCache()
    service = PlacesService(
        places_provider=FakePlacesProvider(),
        cache=cache,
    )
    live_result, _ = service.search_restaurants(restaurant_request)
    assert live_result.data_status is PlacesDataStatus.LIVE

    failing_service = PlacesService(
        places_provider=FakePlacesProvider(should_fail=True),
        cache=cache,
    )
    cached_result, metadata = failing_service.search_restaurants(restaurant_request)
    assert cached_result.data_status is PlacesDataStatus.CACHED
    assert metadata.cache_status == "hit"


def test_unavailable_without_cache(restaurant_request: RestaurantSearchRequest) -> None:
    service = PlacesService(
        places_provider=FakePlacesProvider(should_fail=True),
        cache=PlacesCache(),
    )
    result, metadata = service.search_restaurants(restaurant_request)
    assert result.data_status is PlacesDataStatus.UNAVAILABLE
    assert result.error_message
    assert metadata.cache_status == "miss"


def test_cache_hit(restaurant_request: RestaurantSearchRequest) -> None:
    cache = PlacesCache()
    service = PlacesService(
        places_provider=FakePlacesProvider(),
        cache=cache,
    )
    service.search_restaurants(restaurant_request)
    service.search_restaurants(restaurant_request)
    assert cache.get(PlacesCache.restaurant_cache_key(restaurant_request)) is not None


def test_cache_expiry(restaurant_request: RestaurantSearchRequest) -> None:
    cache = PlacesCache(ttl_seconds=1)
    service = PlacesService(
        places_provider=FakePlacesProvider(),
        cache=cache,
    )
    service.search_restaurants(restaurant_request)
    key = PlacesCache.restaurant_cache_key(restaurant_request)
    entry = cache.get(key)
    assert entry is not None
    stale_time = datetime.now(UTC) - timedelta(seconds=2)
    cache._entries[key] = type(entry)(result=entry.result, stored_at=stale_time)
    assert cache.get(key) is None


def test_deterministic_cache_key() -> None:
    request_a = RestaurantSearchRequest(
        location=DUBAI, cuisine=RestaurantCuisine.ITALIAN
    )
    request_b = RestaurantSearchRequest(
        location=DUBAI, cuisine=RestaurantCuisine.ITALIAN
    )
    request_c = RestaurantSearchRequest(location=DUBAI, cuisine=RestaurantCuisine.THAI)
    assert PlacesCache.restaurant_cache_key(
        request_a
    ) == PlacesCache.restaurant_cache_key(request_b)
    assert PlacesCache.restaurant_cache_key(
        request_a
    ) != PlacesCache.restaurant_cache_key(request_c)


def test_restaurant_and_attraction_cache_keys_do_not_collide(
    restaurant_request: RestaurantSearchRequest,
    attraction_request: AttractionSearchRequest,
) -> None:
    restaurant_key = PlacesCache.restaurant_cache_key(restaurant_request)
    attraction_key = PlacesCache.attraction_cache_key(attraction_request)
    assert restaurant_key != attraction_key


@pytest.mark.asyncio
async def test_mcp_tool_discovery_and_invocation(
    restaurant_request: RestaurantSearchRequest,
    attraction_request: AttractionSearchRequest,
) -> None:
    from mcp import Client

    service = PlacesService(
        places_provider=FakePlacesProvider(),
        cache=PlacesCache(),
    )
    server = create_places_mcp_server(service)

    async with Client(server) as client:
        restaurant_result = await client.call_tool(
            "search_restaurants",
            {
                "location_name": restaurant_request.location.name,
                "latitude": restaurant_request.location.latitude,
                "longitude": restaurant_request.location.longitude,
                "radius_meters": restaurant_request.radius_meters,
                "cuisine": restaurant_request.cuisine.value,
                "price_levels": [
                    level.value for level in restaurant_request.price_levels
                ],
                "max_results": restaurant_request.max_results,
                "language_code": restaurant_request.language_code,
                "region_code": restaurant_request.region_code,
            },
        )
        attraction_result = await client.call_tool(
            "search_attractions",
            {
                "location_name": attraction_request.location.name,
                "latitude": attraction_request.location.latitude,
                "longitude": attraction_request.location.longitude,
                "radius_meters": attraction_request.radius_meters,
                "categories": [
                    category.value for category in attraction_request.categories
                ],
                "max_results": attraction_request.max_results,
                "language_code": attraction_request.language_code,
                "region_code": attraction_request.region_code,
            },
        )

    restaurant_payload = restaurant_result.structured_content
    attraction_payload = attraction_result.structured_content
    assert restaurant_payload["data_status"] == PlacesDataStatus.LIVE.value
    assert restaurant_payload["restaurants"]
    assert attraction_payload["data_status"] == PlacesDataStatus.LIVE.value
    assert attraction_payload["attractions"]
