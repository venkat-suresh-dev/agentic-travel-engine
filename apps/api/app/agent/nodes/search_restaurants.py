"""Search restaurants for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from mcp_tools.distance.locations.base import LocationResolver

from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.tool_runner import ToolExecuteResult, run_bounded_tool_node
from app.agent.state import AgentState, trip_request_from_state
from app.tools.restaurants import RestaurantTool
from app.tools.restaurants_request import build_restaurant_search_request


def build_search_restaurants_node(
    restaurant_tool: RestaurantTool,
    location_resolver: LocationResolver,
    limiter: ToolConcurrencyLimiter,
) -> Callable[[AgentState], AgentState]:
    """Create a restaurant search node bound to the provided tool."""

    def search_restaurants(state: AgentState) -> AgentState:
        """Fetch normalized restaurant results for validated complete requirements."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {}

        def execute() -> ToolExecuteResult:
            request = build_restaurant_search_request(trip_request, location_resolver)
            result, metadata = restaurant_tool.search_restaurants(request)
            return (
                {
                    "restaurant_search": result.model_dump(mode="json"),
                    "restaurant_tool_metadata": metadata.model_dump(mode="json"),
                },
                metadata.provider,
            )

        return run_bounded_tool_node(
            tool_name="search_restaurants",
            limiter=limiter,
            execute=execute,
        )

    return search_restaurants
