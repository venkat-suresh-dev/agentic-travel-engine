"""Produce structured clarification requests for missing requirements."""

from __future__ import annotations

from app.agent.state import AgentState, GraphStatus, validation_from_state
from app.domain.trip_request import FIELD_PROMPTS, ClarificationRequest


def ask_user(state: AgentState) -> AgentState:
    """Build structured clarification metadata for missing fields."""
    validation = validation_from_state(state)
    missing_fields = validation.missing_fields if validation is not None else []

    prompts = {
        field_name: FIELD_PROMPTS[field_name]
        for field_name in missing_fields
        if field_name in FIELD_PROMPTS
    }
    clarification = ClarificationRequest(
        missing_fields=missing_fields,
        prompts=prompts,
        message=(
            "Additional trip details are required before planning can continue."
            if missing_fields
            else "No clarification is required."
        ),
    )

    return {
        "clarification": clarification.model_dump(mode="json"),
        "status": GraphStatus.AWAITING_USER.value,
    }
