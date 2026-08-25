"""Application service boundary for invoking the trip planner graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from mcp_tools.weather.schemas import WeatherForecastResult, WeatherToolMetadata

from app.agent.graph import CompiledTripPlannerGraph, compile_trip_planner_graph
from app.agent.state import (
    AgentInput,
    AgentState,
    GraphStatus,
    clarification_from_state,
    trip_request_from_state,
    validation_from_state,
    weather_forecast_from_state,
    weather_metadata_from_state,
)
from app.domain.trip_request import ClarificationRequest, TripRequest, ValidationResult
from app.llm.base import LLMAdapter
from app.tools.weather import WeatherTool


@dataclass(frozen=True, slots=True)
class TripPlannerRunResult:
    """Normalized graph execution result for API and test consumers."""

    thread_id: str
    status: GraphStatus
    trip_request: TripRequest | None
    validation: ValidationResult | None
    clarification: ClarificationRequest | None
    weather_forecast: WeatherForecastResult | None
    weather_tool_metadata: WeatherToolMetadata | None
    state: AgentState


class TripPlannerAgentService:
    """Invoke and resume the trip planner LangGraph without exposing node internals."""

    def __init__(
        self,
        graph: CompiledTripPlannerGraph | None = None,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        llm_adapter: LLMAdapter | None = None,
        weather_tool: WeatherTool | None = None,
    ) -> None:
        self._checkpointer = checkpointer or InMemorySaver()
        self._graph = graph or compile_trip_planner_graph(
            checkpointer=self._checkpointer,
            llm_adapter=llm_adapter,
            weather_tool=weather_tool,
        )

    def start(
        self,
        user_request: str,
        *,
        thread_id: str | None = None,
    ) -> TripPlannerRunResult:
        """Run the graph for a new planning request."""
        resolved_thread_id = thread_id or str(uuid4())
        graph_input: AgentInput = {"user_request": user_request}
        config: RunnableConfig = {"configurable": {"thread_id": resolved_thread_id}}
        state = self._invoke(graph_input, config)
        return self._to_result(resolved_thread_id, state)

    def resume(
        self,
        thread_id: str,
        user_clarification: str,
    ) -> TripPlannerRunResult:
        """Resume a paused graph thread with additional user clarification."""
        graph_input: AgentInput = {"user_clarification": user_clarification}
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        state = self._invoke(graph_input, config)
        return self._to_result(thread_id, state)

    def get_state(self, thread_id: str) -> TripPlannerRunResult | None:
        """Read the latest checkpointed graph state for a thread."""
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        snapshot = self._graph.get_state(config)
        if snapshot.values is None:
            return None
        state = cast(AgentState, dict(snapshot.values))
        return self._to_result(thread_id, state)

    def _invoke(self, graph_input: AgentInput, config: RunnableConfig) -> AgentState:
        result = self._graph.invoke(graph_input, config=config)
        return cast(AgentState, dict(result))

    def _to_result(self, thread_id: str, state: AgentState) -> TripPlannerRunResult:
        status_value = state.get("status", GraphStatus.EXTRACTING.value)
        return TripPlannerRunResult(
            thread_id=thread_id,
            status=GraphStatus(status_value),
            trip_request=trip_request_from_state(state),
            validation=validation_from_state(state),
            clarification=clarification_from_state(state),
            weather_forecast=weather_forecast_from_state(state),
            weather_tool_metadata=weather_metadata_from_state(state),
            state=state,
        )
