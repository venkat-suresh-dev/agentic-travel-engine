"""Build grounded itinerary draft after budget computation."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import AgentState
from app.itinerary.composer.base import ItineraryComposer
from app.itinerary.from_state import build_itinerary_draft_from_state


def build_build_itinerary_node(
    *,
    composer: ItineraryComposer | None = None,
) -> Callable[[AgentState], dict[str, object]]:
    def build_itinerary(state: AgentState) -> dict[str, object]:
        attempt = int(state.get("itinerary_attempt") or 0) + 1
        result = build_itinerary_draft_from_state(state, composer=composer)
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

    return build_itinerary
