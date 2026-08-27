"""Finalize graph execution after modification critic retries are exhausted."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import AgentState, GraphStatus, critic_result_from_state


def build_finalize_modification_failure_node() -> Callable[[AgentState], AgentState]:
    def finalize_modification_failure(state: AgentState) -> AgentState:
        from app.modification.schemas import ModificationFailure, ModificationStatus

        critic = critic_result_from_state(state)
        previous = state.get("previous_itinerary")
        existing = state.get("modification_failure")
        if existing is not None:
            failure = ModificationFailure.model_validate(existing)
        else:
            failure = ModificationFailure(
                message="itinerary modification critic retries exhausted",
                issues=[
                    issue.message
                    for issue in (critic.issues if critic is not None else [])
                ],
                preserved_itinerary=True,
            )
        return {
            "status": GraphStatus.COMPLETE.value,
            "modification_status": ModificationStatus.FAILED.value,
            "itinerary": previous,
            "itinerary_draft": None,
            "itinerary_build_success": False,
            "planning_failed": False,
            "modification_failure": failure.model_dump(mode="json"),
        }

    return finalize_modification_failure
