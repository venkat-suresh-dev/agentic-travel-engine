"""LangGraph fan-out helpers for independent travel-data tools."""

from __future__ import annotations

from langgraph.types import Send

from app.agent.state import AgentState

INDEPENDENT_TOOL_NODE_NAMES: tuple[str, ...] = (
    "fetch_weather",
    "search_flights",
    "search_hotels",
    "get_distance_matrix",
    "search_restaurants",
    "search_attractions",
)


def fan_out_independent_tools(state: AgentState) -> list[Send]:
    """Return LangGraph Send packets for the independent tool fan-out."""
    return [Send(node_name, state) for node_name in INDEPENDENT_TOOL_NODE_NAMES]
