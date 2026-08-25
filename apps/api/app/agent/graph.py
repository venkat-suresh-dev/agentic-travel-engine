"""Trip planner LangGraph definition."""

from __future__ import annotations

from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes.ask_user import ask_user
from app.agent.nodes.extract_requirements import build_extract_requirements_node
from app.agent.nodes.fetch_weather import build_fetch_weather_node
from app.agent.nodes.validate_requirements import validate_requirements
from app.agent.routing import route_after_validation
from app.agent.state import AgentInput, AgentState
from app.llm.base import LLMAdapter
from app.llm.factory import build_llm_adapter
from app.tools.weather import WeatherTool

CompiledTripPlannerGraph = CompiledStateGraph[AgentState, None, AgentInput, AgentState]


def build_trip_planner_graph(
    llm_adapter: LLMAdapter | None = None,
    weather_tool: WeatherTool | None = None,
) -> StateGraph[AgentState, None, AgentInput, AgentState]:
    """Construct the extract → validate → ask_user/weather state machine."""
    adapter = llm_adapter or build_llm_adapter()
    tool = weather_tool or WeatherTool()
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
        cast(Any, build_fetch_weather_node(tool)),
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
    builder.add_edge("fetch_weather", END)
    return builder


def compile_trip_planner_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    llm_adapter: LLMAdapter | None = None,
    weather_tool: WeatherTool | None = None,
) -> CompiledTripPlannerGraph:
    """Compile the trip planner graph with an optional checkpoint backend."""
    saver = checkpointer or InMemorySaver()
    return build_trip_planner_graph(
        llm_adapter=llm_adapter,
        weather_tool=weather_tool,
    ).compile(
        checkpointer=saver,
    )
