"""Map LangGraph execution events to agent run SSE events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from app.agent.orchestration.schemas import ToolExecutionStatus
from app.agent.state import AgentInput, AgentState, GraphStatus
from app.services.agent_run_events import (
    TOOL_NODE_NAMES,
    TRACKED_NODE_NAMES,
    AgentRunEventPublisher,
)


def _tool_status_from_state(update: dict[str, Any]) -> str:
    records = update.get("tool_orchestration")
    if not isinstance(records, list) or not records:
        return "success"
    latest = records[-1]
    if not isinstance(latest, dict):
        return "success"
    status = latest.get("status", ToolExecutionStatus.SUCCESS.value)
    if status == ToolExecutionStatus.UNAVAILABLE.value:
        return "unavailable"
    if status == ToolExecutionStatus.ERROR.value:
        return "failed"
    if status == ToolExecutionStatus.SKIPPED.value:
        return "skipped"
    return "success"


def invoke_with_events(
    service: Any,
    graph_input: AgentInput,
    config: RunnableConfig,
    publisher: AgentRunEventPublisher,
    *,
    operation_type: str | None = None,
) -> AgentState:
    """Execute the graph while publishing real LangGraph node updates."""
    publisher.run_started(operation_type=operation_type)
    graph = service._graph  # noqa: SLF001 - internal streaming bridge
    final_state: AgentState = cast(AgentState, {})
    started_nodes: set[str] = set()

    for chunk in graph.stream(graph_input, config=config, stream_mode="updates"):
        if not isinstance(chunk, dict):
            continue
        for node_name, update in chunk.items():
            if node_name not in TRACKED_NODE_NAMES:
                continue
            if node_name not in started_nodes:
                started_nodes.add(node_name)
                publisher.node_started(node_name)

            status = "success"
            error_message: str | None = None
            if isinstance(update, dict):
                status = _tool_status_from_state(update)
                if node_name in TOOL_NODE_NAMES:
                    records = update.get("tool_orchestration")
                    if isinstance(records, list) and records:
                        latest = records[-1]
                        if isinstance(latest, dict):
                            error_message = latest.get("error_message")
                final_state = cast(AgentState, {**final_state, **update})
                status_value = update.get("status")
                if isinstance(status_value, str):
                    publisher.run_status_changed(status_value)

            if status == "failed":
                publisher.node_failed(
                    node_name,
                    error_message=error_message or "Node execution failed",
                )
            else:
                publisher.node_completed(node_name, status=status)

    if not final_state:
        snapshot = graph.get_state(config)
        if snapshot.values is not None:
            final_state = cast(AgentState, dict(snapshot.values))

    planning_failed = bool(final_state.get("planning_failed"))
    if planning_failed:
        publisher.run_failed(message="Planning failed")
    else:
        status_value = final_state.get("status", GraphStatus.EXTRACTING.value)
        publisher.run_completed(summary={"status": str(status_value)})

    return final_state


def invoke_with_optional_events(
    service: Any,
    graph_input: AgentInput,
    config: RunnableConfig,
    publisher: AgentRunEventPublisher | None,
    *,
    operation_type: str | None = None,
    fallback: Callable[[], AgentState],
) -> AgentState:
    if publisher is None:
        return fallback()
    return invoke_with_events(
        service,
        graph_input,
        config,
        publisher,
        operation_type=operation_type,
    )
