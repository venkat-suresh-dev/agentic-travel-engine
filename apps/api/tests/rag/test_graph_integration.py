"""Graph integration tests for optional retrieve_context node."""

from __future__ import annotations

from app.agent.graph import compile_trip_planner_graph
from app.agent.routing import route_after_retrieve_context, route_after_validation
from app.agent.state import AgentState
from tests.fakes.llm import FakeLLMAdapter


def test_validation_routes_to_retrieve_context_for_complete_requests() -> None:
    state: AgentState = {
        "validation": {
            "is_complete": True,
            "missing_fields": [],
        }
    }
    assert route_after_validation(state) == "retrieve_context"


def test_retrieve_context_routes_to_parallel_tool_fan_out() -> None:
    result = route_after_retrieve_context({})
    assert isinstance(result, list)
    node_names = {send.node for send in result}
    assert "fetch_weather" in node_names
    assert "search_flights" in node_names
    assert len(node_names) == 6


def test_graph_compiles_with_optional_rag_retriever_none() -> None:
    graph = compile_trip_planner_graph(llm_adapter=FakeLLMAdapter.from_stub())
    assert graph is not None
