"""MCP server exposing the flight search tool."""

from __future__ import annotations

from datetime import date

from mcp.server import MCPServer

from mcp_tools.flights.schemas import (
    CabinClass,
    FlightSearchRequest,
    FlightSearchResult,
)
from mcp_tools.flights.service import FlightService

FLIGHT_MCP_SERVER_NAME = "agentic-travel-flights"


def create_flights_mcp_server(
    flight_service: FlightService | None = None,
) -> MCPServer:
    """Create an MCP server with a single flight search tool."""
    if flight_service is None:
        msg = "flight_service is required to create the flights MCP server"
        raise ValueError(msg)

    server = MCPServer(FLIGHT_MCP_SERVER_NAME)

    @server.tool()
    def search_flights(
        origin: str,
        destination: str,
        departure_date: date,
        travelers: int,
        currency: str,
        return_date: date | None = None,
        cabin_class: CabinClass = CabinClass.ECONOMY,
    ) -> FlightSearchResult:
        """Return normalized flight search offers for a route and date window."""
        request = FlightSearchRequest(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            travelers=travelers,
            cabin_class=cabin_class,
            currency=currency,
        )
        result, _metadata = flight_service.search_flights(request)
        return result

    return server
