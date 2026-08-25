"""Graph routing helpers."""

from __future__ import annotations

from typing import Literal

from langgraph.types import Send

from app.agent.orchestration.fan_out import fan_out_independent_tools
from app.agent.state import AgentState, critic_result_from_state, validation_from_state
from app.itinerary.critic.constants import MAX_ITINERARY_RETRIES

RouteAfterValidation = Literal["retrieve_context", "ask_user"]
RouteAfterRetrieveContext = list[Send]
RouteAfterCritic = Literal["finalize_run", "build_itinerary", "finalize_failure"]


def route_after_validation(state: AgentState) -> RouteAfterValidation:
    """Route complete requirements to context retrieval; otherwise ask user."""
    validation = validation_from_state(state)
    if validation is not None and validation.is_complete:
        return "retrieve_context"
    return "ask_user"


def route_after_retrieve_context(state: AgentState) -> RouteAfterRetrieveContext:
    """Fan out independent tools after optional RAG context retrieval."""
    _ = state
    return fan_out_independent_tools(state)


def route_after_critic(state: AgentState) -> RouteAfterCritic:
    """Route approved itineraries to finalize, retry drafts, or fail."""
    critic = critic_result_from_state(state)
    if critic is not None and critic.valid:
        return "finalize_run"

    attempt = int(state.get("itinerary_attempt") or 0)
    if attempt <= MAX_ITINERARY_RETRIES:
        return "build_itinerary"
    return "finalize_failure"
