"""Construct production places tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.places.cache import PlacesCache
from mcp_tools.places.providers.geoapify import GeoapifyPlacesProvider
from mcp_tools.places.providers.google_places import GooglePlacesProvider
from mcp_tools.places.service import PlacesService

from app.core.config import Settings, settings
from app.tools.attractions import AttractionTool
from app.tools.restaurants import RestaurantTool

GEOAPIFY_SOURCE = "geoapify"


def build_places_service(config: Settings | None = None) -> PlacesService:
    cfg = config or settings
    provider_name = cfg.places_provider.lower()

    if provider_name == "google":
        return PlacesService(
            places_provider=GooglePlacesProvider(
                api_key=cfg.google_places_api_key,
                base_url=cfg.google_places_base_url,
                timeout_seconds=cfg.places_request_timeout_seconds,
            ),
            cache=PlacesCache(ttl_seconds=cfg.places_cache_ttl_seconds),
            source="google-places",
        )
    if provider_name == "geoapify":
        return PlacesService(
            places_provider=GeoapifyPlacesProvider(
                api_key=cfg.geoapify_api_key,
                base_url=cfg.geoapify_base_url,
                timeout_seconds=cfg.places_request_timeout_seconds,
            ),
            cache=PlacesCache(ttl_seconds=cfg.places_cache_ttl_seconds),
            source=GEOAPIFY_SOURCE,
        )

    msg = f"Unsupported places provider: {cfg.places_provider}"
    raise ValueError(msg)


def build_restaurant_tool(config: Settings | None = None) -> RestaurantTool:
    return RestaurantTool(build_places_service(config))


def build_attraction_tool(config: Settings | None = None) -> AttractionTool:
    return AttractionTool(build_places_service(config))
