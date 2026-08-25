"""Finalize graph execution after critic retries are exhausted."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.agent.orchestration.aggregate import (
    build_orchestration_summary,
    compute_aggregate_run_status,
)
from app.agent.state import AgentState, GraphStatus, critic_result_from_state


def build_finalize_failure_node() -> Callable[[AgentState], AgentState]:
    def finalize_failure(state: AgentState) -> AgentState:
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
        critic = critic_result_from_state(state)
        return {
            "aggregate_run_status": aggregate_status.value,
            "tool_orchestration_summary": summary.model_dump(mode="json"),
            "status": GraphStatus.COMPLETE.value,
            "planning_failed": True,
            "itinerary": None,
            "itinerary_build_success": False,
            "planning_failure": {
                "message": "itinerary critic retries exhausted",
                "attempts": state.get("itinerary_attempt"),
                "critic_valid": critic.valid if critic is not None else False,
                "issue_count": len(critic.issues) if critic is not None else 0,
            },
        }

    return finalize_failure
