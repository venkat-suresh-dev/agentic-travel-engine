"""Construct production flight tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.flights.airports.amadeus import AmadeusAirportCodeResolver
from mcp_tools.flights.airports.base import AirportCodeResolver
from mcp_tools.flights.cache import FlightCache
from mcp_tools.flights.providers.amadeus import AmadeusFlightProvider
from mcp_tools.flights.providers.amadeus_auth import AmadeusAuthClient
from mcp_tools.flights.service import FlightService

from app.core.config import Settings, settings
from app.tools.flights import FlightTool


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
    provider = AmadeusFlightProvider(
        client_id=cfg.amadeus_client_id,
        client_secret=cfg.amadeus_client_secret,
        base_url=cfg.amadeus_base_url,
        timeout_seconds=cfg.flights_request_timeout_seconds,
    )
    return FlightService(
        flight_provider=provider,
        cache=FlightCache(ttl_seconds=cfg.flights_cache_ttl_seconds),
    )


def build_airport_resolver(config: Settings | None = None) -> AirportCodeResolver:
    cfg = config or settings
    auth_client = build_amadeus_auth_client(cfg)
    return AmadeusAirportCodeResolver(
        auth_client,
        base_url=cfg.amadeus_base_url,
        timeout_seconds=cfg.flights_request_timeout_seconds,
    )


def build_flight_tool(config: Settings | None = None) -> FlightTool:
    return FlightTool(build_flight_service(config))
