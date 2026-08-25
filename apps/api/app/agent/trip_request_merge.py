"""Merge extracted trip requirements without inventing values."""

from __future__ import annotations

from app.domain.trip_request import TripRequest


def merge_trip_requests(existing: TripRequest, extracted: TripRequest) -> TripRequest:
    """Preserve previously extracted values unless the new extraction updates them."""
    merged = existing.model_copy(deep=True)

    for field_name in TripRequest.model_fields:
        new_value = getattr(extracted, field_name)

        if field_name == "preferences":
            if new_value:
                merged.preferences = list(dict.fromkeys(merged.preferences + new_value))
            continue

        if field_name == "budget_currency":
            if extracted.budget_amount is not None and new_value is not None:
                merged.budget_currency = new_value
            continue

        if new_value is not None:
            setattr(merged, field_name, new_value)

    return merged
