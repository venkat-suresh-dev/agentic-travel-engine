"""MCP server exposing restaurant and attraction search tools."""

from __future__ import annotations

from mcp.server import MCPServer

from mcp_tools.places.schemas import (
    AttractionCategory,
    AttractionSearchRequest,
    AttractionSearchResult,
    RestaurantCuisine,
    RestaurantPriceLevel,
    RestaurantSearchRequest,
    RestaurantSearchResult,
    SearchLocation,
)
from mcp_tools.places.service import PlacesService

PLACES_MCP_SERVER_NAME = "agentic-travel-places"


def create_places_mcp_server(
    places_service: PlacesService | None = None,
) -> MCPServer:
    """Create an MCP server with restaurant and attraction search tools."""
    if places_service is None:
        msg = "places_service is required to create the places MCP server"
        raise ValueError(msg)

    server = MCPServer(PLACES_MCP_SERVER_NAME)

    @server.tool()
    def search_restaurants(
        location_name: str,
        latitude: float,
        longitude: float,
        radius_meters: int = 5_000,
        cuisine: RestaurantCuisine | None = None,
        price_levels: list[RestaurantPriceLevel] | None = None,
        max_results: int = 10,
        language_code: str | None = None,
        region_code: str | None = None,
    ) -> RestaurantSearchResult:
        """Return normalized restaurant search results near a location."""
        request = RestaurantSearchRequest(
            location=SearchLocation(
                name=location_name,
                latitude=latitude,
                longitude=longitude,
            ),
            radius_meters=radius_meters,
            cuisine=cuisine,
            price_levels=price_levels or [],
            max_results=max_results,
            language_code=language_code,
            region_code=region_code,
        )
        result, _metadata = places_service.search_restaurants(request)
        return result

    @server.tool()
    def search_attractions(
        location_name: str,
        latitude: float,
        longitude: float,
        radius_meters: int = 5_000,
        categories: list[AttractionCategory] | None = None,
        max_results: int = 10,
        language_code: str | None = None,
        region_code: str | None = None,
    ) -> AttractionSearchResult:
        """Return normalized attraction search results near a location."""
        request = AttractionSearchRequest(
            location=SearchLocation(
                name=location_name,
                latitude=latitude,
                longitude=longitude,
            ),
            radius_meters=radius_meters,
            categories=categories or [AttractionCategory.TOURIST_ATTRACTION],
            max_results=max_results,
            language_code=language_code,
            region_code=region_code,
        )
        result, _metadata = places_service.search_attractions(request)
        return result

    return server
