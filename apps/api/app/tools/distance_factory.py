"""Construct production distance tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.distance.cache import DistanceCache
from mcp_tools.distance.locations.base import LocationResolver
from mcp_tools.distance.locations.geocoding import GeocodingLocationResolver
from mcp_tools.distance.providers.openrouteservice import (
    OpenRouteServiceDistanceProvider,
)
from mcp_tools.distance.service import DistanceService
from mcp_tools.weather.geocoding.open_meteo import OpenMeteoGeocodingProvider

from app.core.config import Settings, settings
from app.tools.distance import DistanceTool


def build_distance_service(config: Settings | None = None) -> DistanceService:
    cfg = config or settings
    provider = OpenRouteServiceDistanceProvider(
        api_key=cfg.openrouteservice_api_key,
        base_url=cfg.openrouteservice_base_url,
        timeout_seconds=cfg.distance_request_timeout_seconds,
    )
    return DistanceService(
        distance_provider=provider,
        cache=DistanceCache(ttl_seconds=cfg.distance_cache_ttl_seconds),
    )


def build_location_resolver(config: Settings | None = None) -> LocationResolver:
    cfg = config or settings
    geocoding = OpenMeteoGeocodingProvider(
        timeout_seconds=cfg.distance_request_timeout_seconds,
    )
    return GeocodingLocationResolver(geocoding)


def build_distance_tool(config: Settings | None = None) -> DistanceTool:
    return DistanceTool(build_distance_service(config))
