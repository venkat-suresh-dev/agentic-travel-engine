"""Construct production flight tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.flights.airports.amadeus import AmadeusAirportCodeResolver
from mcp_tools.flights.airports.base import AirportCodeResolver
from mcp_tools.flights.airports.static import StaticAirportCodeResolver
from mcp_tools.flights.cache import FlightCache
from mcp_tools.flights.providers.amadeus import AmadeusFlightProvider
from mcp_tools.flights.providers.amadeus_auth import AmadeusAuthClient
from mcp_tools.flights.providers.serpapi import SerpApiFlightProvider
from mcp_tools.flights.service import FlightService

from app.core.config import Settings, settings
from app.tools.flights import FlightTool

SERPAPI_SOURCE = "serpapi-google-flights"


def build_amadeus_auth_client(config: Settings | None = None) -> AmadeusAuthClient:
    cfg = config or settings
    return AmadeusAuthClient(
        client_id=cfg.amadeus_client_id,
        client_secret=cfg.amadeus_client_secret,
        base_url=cfg.amadeus_base_url,
        timeout_seconds=cfg.flights_request_timeout_seconds,
    )


def build_flight_service(config: Settings | None = None) -> FlightService:
    cfg = config or settings
    provider_name = cfg.flights_provider.lower()

    if provider_name == "amadeus":
        return FlightService(
            flight_provider=AmadeusFlightProvider(
                client_id=cfg.amadeus_client_id,
                client_secret=cfg.amadeus_client_secret,
                base_url=cfg.amadeus_base_url,
                timeout_seconds=cfg.flights_request_timeout_seconds,
            ),
            cache=FlightCache(ttl_seconds=cfg.flights_cache_ttl_seconds),
            source="amadeus",
        )
    if provider_name in {"serpapi", "serpapi_google_flights", "google_flights"}:
        return FlightService(
            flight_provider=SerpApiFlightProvider(
                api_key=cfg.serpapi_api_key,
                base_url=cfg.serpapi_base_url,
                engine=cfg.serpapi_flights_engine,
                timeout_seconds=cfg.flights_request_timeout_seconds,
            ),
            cache=FlightCache(ttl_seconds=cfg.flights_cache_ttl_seconds),
            source=SERPAPI_SOURCE,
        )

    msg = f"Unsupported flights provider: {cfg.flights_provider}"
    raise ValueError(msg)


def build_airport_resolver(config: Settings | None = None) -> AirportCodeResolver:
    cfg = config or settings
    provider_name = cfg.flights_provider.lower()

    if provider_name == "amadeus":
        auth_client = build_amadeus_auth_client(cfg)
        return AmadeusAirportCodeResolver(
            auth_client,
            base_url=cfg.amadeus_base_url,
            timeout_seconds=cfg.flights_request_timeout_seconds,
        )

    if provider_name in {"serpapi", "serpapi_google_flights", "google_flights"}:
        return StaticAirportCodeResolver()

    msg = f"Unsupported flights provider for airport resolver: {cfg.flights_provider}"
    raise ValueError(msg)


def build_flight_tool(config: Settings | None = None) -> FlightTool:
    return FlightTool(build_flight_service(config))
