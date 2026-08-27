"""Deterministic modification-intent extraction from user text.

Used as the Groq fallback so supported phrases still resolve when the LLM
is unavailable. The LLM remains the primary extractor when it succeeds.
"""

from __future__ import annotations

import re

from app.modification.schemas import ModificationIntent, TripModificationRequest


def extract_modification_from_text(text: str) -> TripModificationRequest:
    lowered = text.lower()
    return TripModificationRequest(
        intent=_detect_intent(lowered),
        target_days=_detect_days(lowered),
        target_item_ids=[],
        requested_changes=[text.strip()] if text.strip() else [],
        constraints=[],
        raw_message=text,
    )


def _detect_intent(lowered: str) -> ModificationIntent:
    if "hotel" in lowered:
        return ModificationIntent.CHANGE_HOTEL
    if "restaurant" in lowered or "dinner" in lowered or "lunch" in lowered:
        return ModificationIntent.CHANGE_RESTAURANT
    if "culture" in lowered or "shopping" in lowered:
        return ModificationIntent.CHANGE_PREFERENCE
    if "cheaper" in lowered or "reduce cost" in lowered or "budget" in lowered:
        return ModificationIntent.REDUCE_COST
    if "trip cost" in lowered or ("lower" in lowered and "cost" in lowered):
        return ModificationIntent.REDUCE_COST
    if "activity" in lowered or "attraction" in lowered:
        return ModificationIntent.CHANGE_ACTIVITY
    if (
        "relaxed" in lowered
        or "relax" in lowered
        or "pace" in lowered
        or "rushed" in lowered
        or "slower" in lowered
        or "slow down" in lowered
        or "slow morning" in lowered
        or "reduce travel" in lowered
        or "less travel" in lowered
        or "easy because" in lowered
    ):
        return ModificationIntent.CHANGE_PACE
    if "november" in lowered or "move the trip" in lowered or "change dates" in lowered:
        return ModificationIntent.MODIFY_TRIP_REQUIREMENT
    if "swap" in lowered or "replace" in lowered:
        return ModificationIntent.REPLACE_ITEM
    return ModificationIntent.MODIFY_DAY


def _detect_days(lowered: str) -> list[int]:
    matches = re.findall(r"day\s+(\d+)", lowered)
    return [int(match) for match in matches]
