"""Fetch weather context for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import AgentState, GraphStatus, trip_request_from_state
from app.tools.weather import WeatherTool
from app.tools.weather_request import build_weather_request


def build_fetch_weather_node(
    weather_tool: WeatherTool,
) -> Callable[[AgentState], AgentState]:
    """Create a weather node bound to the provided tool."""

    def fetch_weather(state: AgentState) -> AgentState:
        """Fetch normalized weather for validated complete requirements."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {"status": GraphStatus.COMPLETE.value}

        request = build_weather_request(trip_request)
        forecast, metadata = weather_tool.get_forecast(request)

        return {
            "weather_forecast": forecast.model_dump(mode="json"),
            "weather_tool_metadata": metadata.model_dump(mode="json"),
            "status": GraphStatus.COMPLETE.value,
        }

    return fetch_weather
