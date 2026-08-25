"""Aggregate independent parallel tool results."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.agent.orchestration.aggregate import (
    build_orchestration_summary,
    compute_aggregate_run_status,
)
from app.agent.orchestration.schemas import AggregateRunStatus
from app.agent.state import AgentState


def build_aggregate_independent_tools_node() -> Callable[[AgentState], AgentState]:
    """Create a barrier node that summarizes independent parallel tool outcomes."""

    def aggregate_independent_tools(state: AgentState) -> AgentState:
        aggregate_status = compute_aggregate_run_status(
            state,
            include_currency=False,
        )
        if aggregate_status is AggregateRunStatus.FAILED:
            summary = build_orchestration_summary(
                state,
                aggregate_run_status=aggregate_status,
            )
            return {
                "aggregate_run_status": aggregate_status.value,
                "tool_orchestration_summary": summary.model_dump(mode="json"),
                "tool_fan_out_started_at": state.get("tool_fan_out_started_at")
                or datetime.now(UTC).isoformat(),
            }

        return {
            "aggregate_run_status": aggregate_status.value,
            "tool_fan_out_started_at": state.get("tool_fan_out_started_at")
            or datetime.now(UTC).isoformat(),
        }

    return aggregate_independent_tools
