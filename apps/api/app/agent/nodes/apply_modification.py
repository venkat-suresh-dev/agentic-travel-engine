"""Apply selective itinerary modifications."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import AgentState, itinerary_from_state
from app.itinerary.from_state import build_itinerary_context_from_state
from app.modification.engine import ModificationEngine
from app.modification.schemas import ModificationScope, TripModificationRequest


def build_apply_modification_node() -> Callable[[AgentState], dict[str, object]]:
    engine = ModificationEngine()

    def apply_modification(state: AgentState) -> dict[str, object]:
        attempt = int(state.get("itinerary_attempt") or 0) + 1
        context = build_itinerary_context_from_state(state)
        previous = itinerary_from_state(state)
        raw_request = state.get("modification_request")
        raw_scope = state.get("modification_scope")
        if (
            context is None
            or previous is None
            or raw_request is None
            or raw_scope is None
        ):
            return {
                "itinerary_attempt": attempt,
                "itinerary_build_success": False,
            }

        request = TripModificationRequest.model_validate(raw_request)
        scope = ModificationScope.model_validate(raw_scope)
        result = engine.apply(
            previous_itinerary=previous,
            context=context,
            modification=request,
            scope=scope,
        )
        return {
            "itinerary_attempt": attempt,
            "itinerary": None,
            "itinerary_draft": (
                result.itinerary.model_dump(mode="json") if result.itinerary else None
            ),
            "itinerary_candidate": (
                result.candidate.model_dump(mode="json") if result.candidate else None
            ),
            "itinerary_build_success": result.success,
        }

    return apply_modification
