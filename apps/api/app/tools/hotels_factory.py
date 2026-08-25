"""Construct production hotel tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.hotels.cache import HotelCache
from mcp_tools.hotels.locations.amadeus import AmadeusCityCodeResolver
from mcp_tools.hotels.locations.base import CityCodeResolver
from mcp_tools.hotels.locations.static import StaticCityCodeResolver
from mcp_tools.hotels.providers.amadeus import AmadeusHotelProvider
from mcp_tools.hotels.providers.stayingapi import StayingApiHotelProvider
from mcp_tools.hotels.service import HotelService

from app.core.config import Settings, settings
from app.tools.flights_factory import build_amadeus_auth_client
from app.tools.hotels import HotelTool

STAYINGAPI_SANDBOX_SOURCE = "stayingapi-sandbox"
STAYINGAPI_LIVE_SOURCE = "stayingapi"


def build_hotel_service(config: Settings | None = None) -> HotelService:
    cfg = config or settings
    provider_name = cfg.hotels_provider.lower()

    if provider_name == "amadeus":
        auth_client = build_amadeus_auth_client(cfg)
        return HotelService(
            hotel_provider=AmadeusHotelProvider(
                client_id=cfg.amadeus_client_id,
                client_secret=cfg.amadeus_client_secret,
                base_url=cfg.amadeus_base_url,
                timeout_seconds=cfg.hotels_request_timeout_seconds,
                auth_client=auth_client,
            ),
            cache=HotelCache(ttl_seconds=cfg.hotels_cache_ttl_seconds),
            source="amadeus",
        )
    if provider_name in {"stayingapi", "staying_api"}:
        source = (
            STAYINGAPI_SANDBOX_SOURCE
            if cfg.stayingapi_environment.lower() == "sandbox"
            else STAYINGAPI_LIVE_SOURCE
        )
        return HotelService(
            hotel_provider=StayingApiHotelProvider(
                api_key=cfg.stayingapi_api_key,
                base_url=cfg.stayingapi_base_url,
                environment=cfg.stayingapi_environment,
                timeout_seconds=cfg.hotels_request_timeout_seconds,
            ),
            cache=HotelCache(ttl_seconds=cfg.hotels_cache_ttl_seconds),
            source=source,
        )

    msg = f"Unsupported hotels provider: {cfg.hotels_provider}"
    raise ValueError(msg)


def build_city_resolver(config: Settings | None = None) -> CityCodeResolver:
    cfg = config or settings
    provider_name = cfg.hotels_provider.lower()

    if provider_name == "amadeus":
        auth_client = build_amadeus_auth_client(cfg)
        return AmadeusCityCodeResolver(
            auth_client,
            base_url=cfg.amadeus_base_url,
            timeout_seconds=cfg.hotels_request_timeout_seconds,
        )

    if provider_name in {"stayingapi", "staying_api"}:
        return StaticCityCodeResolver()

    msg = f"Unsupported hotels provider for city resolver: {cfg.hotels_provider}"
    raise ValueError(msg)


def build_hotel_tool(config: Settings | None = None) -> HotelTool:
    return HotelTool(build_hotel_service(config))
