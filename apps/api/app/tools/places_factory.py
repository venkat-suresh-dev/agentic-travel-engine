"""Construct production places tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.places.cache import PlacesCache
from mcp_tools.places.providers.google_places import GooglePlacesProvider
from mcp_tools.places.service import PlacesService

from app.core.config import Settings, settings
from app.tools.attractions import AttractionTool
from app.tools.restaurants import RestaurantTool


def build_places_service(config: Settings | None = None) -> PlacesService:
    cfg = config or settings
    provider = GooglePlacesProvider(
        api_key=cfg.google_places_api_key,
        base_url=cfg.google_places_base_url,
        timeout_seconds=cfg.places_request_timeout_seconds,
    )
    return PlacesService(
        places_provider=provider,
        cache=PlacesCache(ttl_seconds=cfg.places_cache_ttl_seconds),
    )


def build_restaurant_tool(config: Settings | None = None) -> RestaurantTool:
    return RestaurantTool(build_places_service(config))


def build_attraction_tool(config: Settings | None = None) -> AttractionTool:
    return AttractionTool(build_places_service(config))
