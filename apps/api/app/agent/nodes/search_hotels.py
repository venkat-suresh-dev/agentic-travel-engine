"""Search hotels for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from mcp_tools.hotels.locations.base import CityCodeResolver

from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.tool_runner import ToolExecuteResult, run_bounded_tool_node
from app.agent.state import AgentState, trip_request_from_state
from app.tools.hotels import HotelTool
from app.tools.hotels_request import build_hotel_search_request


def build_search_hotels_node(
    hotel_tool: HotelTool,
    city_resolver: CityCodeResolver,
    limiter: ToolConcurrencyLimiter,
) -> Callable[[AgentState], AgentState]:
    """Create a hotel search node bound to the provided tool."""

    def search_hotels(state: AgentState) -> AgentState:
        """Fetch normalized hotel offers for validated complete requirements."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {}

        def execute() -> ToolExecuteResult:
            request = build_hotel_search_request(trip_request, city_resolver)
            result, metadata = hotel_tool.search_hotels(request)
            return (
                {
                    "hotel_search": result.model_dump(mode="json"),
                    "hotel_tool_metadata": metadata.model_dump(mode="json"),
                },
                metadata.provider,
            )

        return run_bounded_tool_node(
            tool_name="search_hotels",
            limiter=limiter,
            execute=execute,
        )

    return search_hotels
