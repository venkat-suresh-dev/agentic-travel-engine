"""Resolve deterministic modification scope and refresh plan."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import AgentState, itinerary_from_state
from app.modification.schemas import TripModificationRequest
from app.modification.scope import build_refresh_plan, resolve_modification_scope


def build_resolve_modification_scope_node() -> Callable[[AgentState], AgentState]:
    def resolve_modification_scope_node(state: AgentState) -> AgentState:
        raw = state.get("modification_request")
        itinerary = itinerary_from_state(state)
        if raw is None or itinerary is None:
            return {}

        request = TripModificationRequest.model_validate(raw)
        scope = resolve_modification_scope(request, itinerary=itinerary)
        refresh_plan = build_refresh_plan(request, scope)
        return {
            "modification_scope": scope.model_dump(mode="json"),
            "refresh_plan": refresh_plan.model_dump(mode="json"),
        }

    return resolve_modification_scope_node
