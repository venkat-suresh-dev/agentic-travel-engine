"""LangGraph state definitions for the trip planning agent."""

from __future__ import annotations

from enum import StrEnum
from typing import TypedDict

from app.domain.trip_request import ClarificationRequest, TripRequest, ValidationResult


class GraphStatus(StrEnum):
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    AWAITING_USER = "awaiting_user"
    COMPLETE = "complete"


class ConversationMessage(TypedDict):
    role: str
    content: str


class AgentState(TypedDict, total=False):
    """Shared LangGraph state for the extract → validate → ask_user loop."""

    user_request: str
    user_clarification: str | None
    messages: list[ConversationMessage]
    trip_request: dict[str, object] | None
    validation: dict[str, object] | None
    clarification: dict[str, object] | None
    status: str


class AgentInput(TypedDict, total=False):
    """External graph input for initial and resumed invocations."""

    user_request: str
    user_clarification: str | None
    messages: list[ConversationMessage]


def trip_request_from_state(state: AgentState) -> TripRequest | None:
    raw = state.get("trip_request")
    if raw is None:
        return None
    return TripRequest.model_validate(raw)


def validation_from_state(state: AgentState) -> ValidationResult | None:
    raw = state.get("validation")
    if raw is None:
        return None
    return ValidationResult.model_validate(raw)


def clarification_from_state(state: AgentState) -> ClarificationRequest | None:
    raw = state.get("clarification")
    if raw is None:
        return None
    return ClarificationRequest.model_validate(raw)
