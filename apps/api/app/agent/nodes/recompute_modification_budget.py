"""Recompute budget after a cost-changing modification."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import AgentState, itinerary_draft_from_state
from app.itinerary.from_state import build_itinerary_context_from_state
from app.modification.engine import ModificationEngine


def build_recompute_modification_budget_node() -> Callable[
    [AgentState], dict[str, object]
]:
    engine = ModificationEngine()

    def recompute_modification_budget(state: AgentState) -> dict[str, object]:
        context = build_itinerary_context_from_state(state)
        draft = itinerary_draft_from_state(state)
        if context is None or draft is None:
            return {}

        budget_result = engine.recompute_budget(context=context, itinerary=draft)
        synced = engine.sync_budget_fields(draft, budget_result)
        return {
            "budget_result": budget_result.model_dump(mode="json"),
            "itinerary_draft": synced.model_dump(mode="json"),
        }

    return recompute_modification_budget
