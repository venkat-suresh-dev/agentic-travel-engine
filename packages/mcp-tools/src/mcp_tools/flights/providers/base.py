"""Flight provider protocol."""

from __future__ import annotations

from typing import Protocol

from mcp_tools.flights.schemas import FlightOffer, FlightSearchRequest


class FlightProvider(Protocol):
    """Search for flight offers from an upstream provider."""

    def search_flights(self, request: FlightSearchRequest) -> list[FlightOffer]: ...
