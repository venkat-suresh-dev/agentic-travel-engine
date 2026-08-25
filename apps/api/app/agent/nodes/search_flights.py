"""Search flights for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from mcp_tools.flights.airports.base import AirportCodeResolver

from app.agent.state import AgentState, GraphStatus, trip_request_from_state
from app.tools.flights import FlightTool
from app.tools.flights_request import build_flight_search_request


def build_search_flights_node(
    flight_tool: FlightTool,
    airport_resolver: AirportCodeResolver,
) -> Callable[[AgentState], AgentState]:
    """Create a flight search node bound to the provided tool."""

    def search_flights(state: AgentState) -> AgentState:
        """Fetch normalized flight offers for validated complete requirements."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {"status": GraphStatus.COMPLETE.value}

        request = build_flight_search_request(trip_request, airport_resolver)
        result, metadata = flight_tool.search_flights(request)

        return {
            "flight_search": result.model_dump(mode="json"),
            "flight_tool_metadata": metadata.model_dump(mode="json"),
            "status": GraphStatus.COMPLETE.value,
        }

    return search_flights
