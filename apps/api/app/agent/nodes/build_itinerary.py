"""Build grounded itinerary after budget computation."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import AgentState
from app.itinerary.composer.base import ItineraryComposer
from app.itinerary.from_state import build_itinerary_from_state


def build_build_itinerary_node(
    *,
    composer: ItineraryComposer | None = None,
) -> Callable[[AgentState], dict[str, object]]:
    def build_itinerary(state: AgentState) -> dict[str, object]:
        result = build_itinerary_from_state(state, composer=composer)
        return {
            "itinerary": (
                result.itinerary.model_dump(mode="json") if result.itinerary else None
            ),
            "itinerary_candidate": (
                result.candidate.model_dump(mode="json") if result.candidate else None
            ),
            "itinerary_validation": result.validation.model_dump(mode="json"),
            "itinerary_build_success": result.success,
        }

    return build_itinerary
