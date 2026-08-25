"""Trip planner LangGraph definition."""

from __future__ import annotations

from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from mcp_tools.flights.airports.base import AirportCodeResolver

from app.agent.nodes.ask_user import ask_user
from app.agent.nodes.extract_requirements import build_extract_requirements_node
from app.agent.nodes.fetch_weather import build_fetch_weather_node
from app.agent.nodes.search_flights import build_search_flights_node
from app.agent.nodes.validate_requirements import validate_requirements
from app.agent.routing import route_after_validation
from app.agent.state import AgentInput, AgentState
from app.llm.base import LLMAdapter
from app.llm.factory import build_llm_adapter
from app.tools.flights import FlightTool
from app.tools.flights_factory import build_airport_resolver, build_flight_tool
from app.tools.weather import WeatherTool

CompiledTripPlannerGraph = CompiledStateGraph[AgentState, None, AgentInput, AgentState]


def build_trip_planner_graph(
    llm_adapter: LLMAdapter | None = None,
    weather_tool: WeatherTool | None = None,
    flight_tool: FlightTool | None = None,
    airport_resolver: AirportCodeResolver | None = None,
) -> StateGraph[AgentState, None, AgentInput, AgentState]:
    """Construct the extract → validate → ask_user/weather/flights state machine."""
    adapter = llm_adapter or build_llm_adapter()
    weather = weather_tool or WeatherTool()
    flights = flight_tool or build_flight_tool()
    resolver = airport_resolver or build_airport_resolver()

    builder: StateGraph[AgentState, None, AgentInput, AgentState] = StateGraph(
        AgentState,
        input_schema=AgentInput,
    )
    builder.add_node(
        "extract_requirements",
        cast(Any, build_extract_requirements_node(adapter)),
    )
    builder.add_node("validate_requirements", validate_requirements)
    builder.add_node("ask_user", ask_user)
    builder.add_node(
        "fetch_weather",
        cast(Any, build_fetch_weather_node(weather)),
    )
    builder.add_node(
        "search_flights",
        cast(Any, build_search_flights_node(flights, resolver)),
    )

    builder.add_edge(START, "extract_requirements")
    builder.add_edge("extract_requirements", "validate_requirements")
    builder.add_conditional_edges(
        "validate_requirements",
        route_after_validation,
        {
            "fetch_weather": "fetch_weather",
            "ask_user": "ask_user",
        },
    )
    builder.add_edge("ask_user", END)
    builder.add_edge("fetch_weather", "search_flights")
    builder.add_edge("search_flights", END)
    return builder


def compile_trip_planner_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    llm_adapter: LLMAdapter | None = None,
    weather_tool: WeatherTool | None = None,
    flight_tool: FlightTool | None = None,
    airport_resolver: AirportCodeResolver | None = None,
) -> CompiledTripPlannerGraph:
    """Compile the trip planner graph with an optional checkpoint backend."""
    saver = checkpointer or InMemorySaver()
    return build_trip_planner_graph(
        llm_adapter=llm_adapter,
        weather_tool=weather_tool,
        flight_tool=flight_tool,
        airport_resolver=airport_resolver,
    ).compile(
        checkpointer=saver,
    )
