"""Fetch distance matrix for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from mcp_tools.distance.locations.base import LocationResolver

from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.tool_runner import ToolExecuteResult, run_bounded_tool_node
from app.agent.state import AgentState, trip_request_from_state
from app.tools.distance import DistanceTool
from app.tools.distance_request import build_distance_matrix_request


def build_get_distance_matrix_node(
    distance_tool: DistanceTool,
    location_resolver: LocationResolver,
    limiter: ToolConcurrencyLimiter,
) -> Callable[[AgentState], AgentState]:
    """Create a distance matrix node bound to the provided tool."""

    def get_distance_matrix(state: AgentState) -> AgentState:
        """Fetch normalized distance facts for validated complete requirements."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {}

        def execute() -> ToolExecuteResult:
            request = build_distance_matrix_request(trip_request, location_resolver)
            result, metadata = distance_tool.get_distance_matrix(request)
            return (
                {
                    "distance_matrix": result.model_dump(mode="json"),
                    "distance_tool_metadata": metadata.model_dump(mode="json"),
                },
                metadata.provider,
            )

        return run_bounded_tool_node(
            tool_name="get_distance_matrix",
            limiter=limiter,
            execute=execute,
        )

    return get_distance_matrix
