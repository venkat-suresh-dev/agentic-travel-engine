"""Finalize graph execution after dependency-aware currency conversion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.agent.orchestration.aggregate import (
    build_orchestration_summary,
    compute_aggregate_run_status,
)
from app.agent.state import AgentState, GraphStatus


def build_finalize_run_node() -> Callable[[AgentState], AgentState]:
    """Create a final node that sets graph completion and orchestration summary."""

    def finalize_run(state: AgentState) -> AgentState:
        aggregate_status = compute_aggregate_run_status(
            state,
            include_currency=True,
        )
        started_raw = state.get("tool_fan_out_started_at")
        started_at = (
            datetime.fromisoformat(started_raw) if started_raw is not None else None
        )
        summary = build_orchestration_summary(
            state,
            aggregate_run_status=aggregate_status,
            started_at=started_at,
        )
        return {
            "aggregate_run_status": aggregate_status.value,
            "tool_orchestration_summary": summary.model_dump(mode="json"),
            "status": GraphStatus.COMPLETE.value,
        }

    return finalize_run
