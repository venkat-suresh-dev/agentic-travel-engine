"""Graph routing helpers."""

from __future__ import annotations

from typing import Literal

from langgraph.types import Send

from app.agent.orchestration.fan_out import fan_out_independent_tools
from app.agent.state import (
    AgentState,
    critic_result_from_state,
    refresh_plan_from_state,
    validation_from_state,
)
from app.itinerary.critic.constants import MAX_ITINERARY_RETRIES
from app.modification.detector import is_completed_plan_modification
from app.modification.refresh_fan_out import fan_out_modification_tools
from app.modification.schemas import ModificationScope, ModificationStatus

RouteEntry = Literal["extract_requirements", "extract_modification"]
RouteAfterValidation = Literal["retrieve_context", "ask_user"]
RouteAfterRetrieveContext = list[Send] | Literal["apply_modification"]
RouteAfterModificationScope = Literal["apply_modification"] | list[Send]
RouteAfterAggregate = Literal["convert_currency", "apply_modification"]
RouteAfterConvertCurrency = Literal["compute_budget", "apply_modification"]
RouteAfterApplyModification = Literal[
    "recompute_modification_budget", "critic_validate"
]
RouteAfterCritic = Literal[
    "finalize_run",
    "build_itinerary",
    "apply_modification",
    "finalize_failure",
    "finalize_modification_failure",
]


def route_entry(state: AgentState) -> RouteEntry:
    """Route initial resume traffic to clarification or modification extraction."""
    if is_completed_plan_modification(state):
        return "extract_modification"
    return "extract_requirements"


def route_after_validation(state: AgentState) -> RouteAfterValidation:
    """Route complete requirements to context retrieval; otherwise ask user."""
    validation = validation_from_state(state)
    if validation is not None and validation.is_complete:
        return "retrieve_context"
    return "ask_user"


def route_after_retrieve_context(
    state: AgentState,
) -> RouteAfterRetrieveContext:
    """Fan out independent tools or continue a modification-only RAG refresh."""
    if state.get("modification_status") == ModificationStatus.IN_PROGRESS.value:
        return "apply_modification"
    return fan_out_independent_tools(state)


def route_after_modification_scope(
    state: AgentState,
) -> RouteAfterModificationScope:
    """Refresh only invalidated providers or apply modification directly."""
    plan = refresh_plan_from_state(state)
    if plan is not None and plan.requires_any_refresh:
        sends = fan_out_modification_tools(state)
        if sends:
            return sends
    return "apply_modification"


def route_after_aggregate(state: AgentState) -> RouteAfterAggregate:
    """Route modification refreshes to apply path; planning to currency."""
    if state.get("modification_status") == ModificationStatus.IN_PROGRESS.value:
        plan = refresh_plan_from_state(state)
        if plan is not None and plan.refresh_currency:
            return "convert_currency"
        return "apply_modification"
    return "convert_currency"


def route_after_convert_currency(state: AgentState) -> RouteAfterConvertCurrency:
    """Continue planning or apply a modification after currency refresh."""
    if state.get("modification_status") == ModificationStatus.IN_PROGRESS.value:
        return "apply_modification"
    return "compute_budget"


def route_after_apply_modification(state: AgentState) -> RouteAfterApplyModification:
    """Recompute budget when a modification changes cost-bearing items."""
    raw_scope = state.get("modification_scope")
    if raw_scope is None:
        return "critic_validate"
    scope = ModificationScope.model_validate(raw_scope)
    if scope.requires_budget_recompute:
        return "recompute_modification_budget"
    return "critic_validate"


def route_after_critic(state: AgentState) -> RouteAfterCritic:
    """Route approved itineraries to finalize, retry drafts, or fail."""
    critic = critic_result_from_state(state)
    if critic is not None and critic.valid:
        return "finalize_run"

    attempt = int(state.get("itinerary_attempt") or 0)
    if state.get("modification_status") == ModificationStatus.IN_PROGRESS.value:
        if attempt <= MAX_ITINERARY_RETRIES:
            return "apply_modification"
        return "finalize_modification_failure"

    if attempt <= MAX_ITINERARY_RETRIES:
        return "build_itinerary"
    return "finalize_failure"
