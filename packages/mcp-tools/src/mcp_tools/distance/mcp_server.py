"""MCP server exposing the distance matrix tool."""

from __future__ import annotations

from mcp.server import MCPServer

from mcp_tools.distance.schemas import (
    DistanceMatrixRequest,
    DistanceMatrixResult,
    LocationPoint,
    TravelMode,
)
from mcp_tools.distance.service import DistanceService

DISTANCE_MCP_SERVER_NAME = "agentic-travel-distance"


def create_distance_mcp_server(
    distance_service: DistanceService | None = None,
) -> MCPServer:
    """Create an MCP server with a single distance matrix tool."""
    if distance_service is None:
        msg = "distance_service is required to create the distance MCP server"
        raise ValueError(msg)

    server = MCPServer(DISTANCE_MCP_SERVER_NAME)

    @server.tool()
    def get_distance_matrix(
        origins: list[LocationPoint],
        destinations: list[LocationPoint],
        travel_mode: TravelMode = TravelMode.DRIVING,
    ) -> DistanceMatrixResult:
        """Return normalized distance and duration between location pairs."""
        request = DistanceMatrixRequest(
            origins=origins,
            destinations=destinations,
            travel_mode=travel_mode,
        )
        result, _metadata = distance_service.get_distance_matrix(request)
        return result

    return server
