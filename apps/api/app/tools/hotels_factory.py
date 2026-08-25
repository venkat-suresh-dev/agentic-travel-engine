"""Construct production hotel tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.hotels.cache import HotelCache
from mcp_tools.hotels.locations.amadeus import AmadeusCityCodeResolver
from mcp_tools.hotels.locations.base import CityCodeResolver
from mcp_tools.hotels.providers.amadeus import AmadeusHotelProvider
from mcp_tools.hotels.service import HotelService

from app.core.config import Settings, settings
from app.tools.flights_factory import build_amadeus_auth_client
from app.tools.hotels import HotelTool


def build_hotel_service(config: Settings | None = None) -> HotelService:
    cfg = config or settings
    auth_client = build_amadeus_auth_client(cfg)
    provider = AmadeusHotelProvider(
        client_id=cfg.amadeus_client_id,
        client_secret=cfg.amadeus_client_secret,
        base_url=cfg.amadeus_base_url,
        timeout_seconds=cfg.hotels_request_timeout_seconds,
        auth_client=auth_client,
    )
    return HotelService(
        hotel_provider=provider,
        cache=HotelCache(ttl_seconds=cfg.hotels_cache_ttl_seconds),
    )


def build_city_resolver(config: Settings | None = None) -> CityCodeResolver:
    cfg = config or settings
    auth_client = build_amadeus_auth_client(cfg)
    return AmadeusCityCodeResolver(
        auth_client,
        base_url=cfg.amadeus_base_url,
        timeout_seconds=cfg.hotels_request_timeout_seconds,
    )


def build_hotel_tool(config: Settings | None = None) -> HotelTool:
    return HotelTool(build_hotel_service(config))
