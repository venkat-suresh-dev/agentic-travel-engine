"""MCP server exposing the hotel search tool."""

from __future__ import annotations

from datetime import date

from mcp.server import MCPServer

from mcp_tools.hotels.schemas import HotelSearchRequest, HotelSearchResult
from mcp_tools.hotels.service import HotelService

HOTEL_MCP_SERVER_NAME = "agentic-travel-hotels"


def create_hotels_mcp_server(
    hotel_service: HotelService | None = None,
) -> MCPServer:
    """Create an MCP server with a single hotel search tool."""
    if hotel_service is None:
        msg = "hotel_service is required to create the hotels MCP server"
        raise ValueError(msg)

    server = MCPServer(HOTEL_MCP_SERVER_NAME)

    @server.tool()
    def search_hotels(
        location: str,
        city_code: str,
        check_in: date,
        check_out: date,
        travelers: int,
        rooms: int,
        currency: str,
    ) -> HotelSearchResult:
        """Return normalized hotel search results for a stay window."""
        request = HotelSearchRequest(
            location=location,
            city_code=city_code,
            check_in=check_in,
            check_out=check_out,
            travelers=travelers,
            rooms=rooms,
            currency=currency,
        )
        result, _metadata = hotel_service.search_hotels(request)
        return result

    return server
