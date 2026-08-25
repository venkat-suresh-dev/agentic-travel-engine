"""Trip planner LangGraph definition."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes.ask_user import ask_user
from app.agent.nodes.extract_requirements import extract_requirements
from app.agent.nodes.validate_requirements import validate_requirements
from app.agent.routing import route_after_validation
from app.agent.state import AgentInput, AgentState

CompiledTripPlannerGraph = CompiledStateGraph[AgentState, None, AgentInput, AgentState]


def build_trip_planner_graph() -> StateGraph[AgentState, None, AgentInput, AgentState]:
    """Construct the extract → validate → ask_user state machine."""
    builder: StateGraph[AgentState, None, AgentInput, AgentState] = StateGraph(
        AgentState,
        input_schema=AgentInput,
    )
    builder.add_node("extract_requirements", extract_requirements)
    builder.add_node("validate_requirements", validate_requirements)
    builder.add_node("ask_user", ask_user)

    builder.add_edge(START, "extract_requirements")
    builder.add_edge("extract_requirements", "validate_requirements")
    builder.add_conditional_edges(
        "validate_requirements",
        route_after_validation,
        {
            "ask_user": "ask_user",
            END: END,
        },
    )
    builder.add_edge("ask_user", END)
    return builder


def compile_trip_planner_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledTripPlannerGraph:
    """Compile the trip planner graph with an optional checkpoint backend."""
    saver = checkpointer or InMemorySaver()
    return build_trip_planner_graph().compile(checkpointer=saver)
