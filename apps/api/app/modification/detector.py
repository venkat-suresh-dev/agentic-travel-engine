"""Detect clarification vs completed-plan modification context."""

from __future__ import annotations

from collections.abc import Mapping


def is_completed_plan_modification(state: Mapping[str, object]) -> bool:
    """Return True when a resume message modifies an approved itinerary."""
    if not state.get("user_clarification"):
        return False
    if state.get("status") == "awaiting_user":
        return False

    validation = state.get("validation")
    if isinstance(validation, dict) and not validation.get("is_complete", False):
        return False

    if state.get("itinerary") is None:
        return False

    return not bool(state.get("planning_failed"))
