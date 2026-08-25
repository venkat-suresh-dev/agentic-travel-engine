"""Flight tool application boundary."""

from __future__ import annotations

from mcp_tools.flights.schemas import (
    FlightSearchRequest,
    FlightSearchResult,
    FlightToolMetadata,
)
from mcp_tools.flights.service import FlightService


class FlightTool:
    """Invoke the MCP-backed flight search capability from the application layer."""

    def __init__(self, flight_service: FlightService | None = None) -> None:
        if flight_service is None:
            msg = "flight_service is required"
            raise ValueError(msg)
        self._flight_service = flight_service

    @property
    def flight_service(self) -> FlightService:
        return self._flight_service

    def search_flights(
        self,
        request: FlightSearchRequest,
    ) -> tuple[FlightSearchResult, FlightToolMetadata]:
        """Fetch normalized flight search results with provenance metadata."""
        result, metadata = self._flight_service.search_flights(request)
        return result, metadata
