"""Graph integration tests for the weather vertical slice."""

from __future__ import annotations

from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.tools.weather import WeatherTool

from tests.fakes.llm import FakeLLMAdapter

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."


def test_complete_request_stores_weather_in_graph_state(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="weather-complete")

    assert result.status == GraphStatus.COMPLETE
    assert result.weather_forecast is not None
    assert result.weather_forecast.data_status.value == "live"
    assert result.weather_forecast.forecast
    assert result.weather_tool_metadata is not None
    assert result.weather_tool_metadata.tool_name == "get_weather_forecast"
    assert result.weather_tool_metadata.provider == "open-meteo"


def test_incomplete_request_does_not_fetch_weather(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
    )

    result = service.start(INCOMPLETE_REQUEST, thread_id="weather-incomplete")

    assert result.status == GraphStatus.AWAITING_USER
    assert result.weather_forecast is None
    assert result.weather_tool_metadata is None
