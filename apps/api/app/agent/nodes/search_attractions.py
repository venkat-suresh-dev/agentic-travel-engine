"""Search attractions for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from mcp_tools.distance.locations.base import LocationResolver

from app.agent.state import AgentState, GraphStatus, trip_request_from_state
from app.tools.attractions import AttractionTool
from app.tools.attractions_request import build_attraction_search_request


def build_search_attractions_node(
    attraction_tool: AttractionTool,
    location_resolver: LocationResolver,
) -> Callable[[AgentState], AgentState]:
    """Create an attraction search node bound to the provided tool."""

    def search_attractions(state: AgentState) -> AgentState:
        """Fetch normalized attraction results for validated complete requirements."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {"status": GraphStatus.COMPLETE.value}

        request = build_attraction_search_request(trip_request, location_resolver)
        result, metadata = attraction_tool.search_attractions(request)

        return {
            "attraction_search": result.model_dump(mode="json"),
            "attraction_tool_metadata": metadata.model_dump(mode="json"),
            "status": GraphStatus.COMPLETE.value,
        }

    return search_attractions
