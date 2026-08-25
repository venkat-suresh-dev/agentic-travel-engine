"""Deterministic modification extraction stub for offline tests."""

from __future__ import annotations

import re

from app.modification.schemas import ModificationIntent, TripModificationRequest


def extract_modification_from_text(text: str) -> TripModificationRequest:
    lowered = text.lower()
    intent = _detect_intent(lowered)
    target_days = _detect_days(lowered)
    return TripModificationRequest(
        intent=intent,
        target_days=target_days,
        target_item_ids=[],
        requested_changes=[text.strip()],
        constraints=[],
        raw_message=text,
    )


def _detect_intent(lowered: str) -> ModificationIntent:
    if "hotel" in lowered:
        return ModificationIntent.CHANGE_HOTEL
    if "restaurant" in lowered or "dinner" in lowered or "lunch" in lowered:
        return ModificationIntent.CHANGE_RESTAURANT
    if "cheaper" in lowered or "reduce cost" in lowered or "budget" in lowered:
        return ModificationIntent.REDUCE_COST
    if "activity" in lowered or "attraction" in lowered:
        return ModificationIntent.CHANGE_ACTIVITY
    if "relaxed" in lowered or "relax" in lowered or "pace" in lowered:
        return ModificationIntent.CHANGE_PACE
    if "november" in lowered or "move the trip" in lowered or "change dates" in lowered:
        return ModificationIntent.MODIFY_TRIP_REQUIREMENT
    if "swap" in lowered or "replace" in lowered:
        return ModificationIntent.REPLACE_ITEM
    return ModificationIntent.MODIFY_DAY


def _detect_days(lowered: str) -> list[int]:
    matches = re.findall(r"day\s+(\d+)", lowered)
    return [int(match) for match in matches]
