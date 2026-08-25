"""Deterministic critic validation for itinerary drafts."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import (
    AgentState,
    itinerary_candidate_from_state,
    itinerary_draft_from_state,
)
from app.itinerary.catalog import build_grounded_catalog
from app.itinerary.critic.engine import ItineraryCritic
from app.itinerary.critic.schemas import (
    CriticIssue,
    CriticIssueCode,
    CriticIssueSeverity,
    CriticResult,
)
from app.itinerary.from_state import build_itinerary_context_from_state


def build_critic_validate_node() -> Callable[[AgentState], dict[str, object]]:
    critic = ItineraryCritic()

    def critic_validate(state: AgentState) -> dict[str, object]:
        context = build_itinerary_context_from_state(state)
        if context is None:
            result = CriticResult(
                valid=False,
                issues=[
                    CriticIssue(
                        code=CriticIssueCode.UNSUPPORTED_ITEM,
                        severity=CriticIssueSeverity.ERROR,
                        message="trip request and budget result are required",
                    )
                ],
                retryable=False,
            )
            return _critic_state_update(result, approved_itinerary=None)

        catalog = build_grounded_catalog(context)
        candidate = itinerary_candidate_from_state(state)
        draft = itinerary_draft_from_state(state)
        result = critic.critique(
            candidate=candidate,
            itinerary=draft,
            context=context,
            catalog=catalog,
        )
        approved = draft.model_dump(mode="json") if result.valid and draft else None
        return _critic_state_update(result, approved_itinerary=approved)

    return critic_validate


def _critic_state_update(
    result: CriticResult,
    *,
    approved_itinerary: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "critic_result": result.model_dump(mode="json"),
        "critic_issues": [issue.model_dump(mode="json") for issue in result.issues],
        "itinerary": approved_itinerary,
        "itinerary_build_success": result.valid,
        "itinerary_validation": {
            "is_valid": result.valid,
            "issues": [
                {
                    "code": issue.code.value,
                    "message": issue.message,
                    "day_number": issue.day_number,
                    "item_id": issue.item_id,
                }
                for issue in result.issues
            ],
        },
        "planning_failed": False if result.valid else None,
    }
