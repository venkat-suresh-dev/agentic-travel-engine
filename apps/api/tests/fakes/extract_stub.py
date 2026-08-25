"""Deterministic extraction stub used by test doubles."""

from __future__ import annotations

import re
from decimal import Decimal

from app.domain.trip_request import TripRequest, TripType

_DURATION_PATTERN = re.compile(r"\b(\d+)\s*[- ]?day", re.IGNORECASE)
_TRAVELERS_PATTERN = re.compile(
    r"\bfor\s+(\d+)\s+(?:people|travelers|persons)\b",
    re.IGNORECASE,
)
_DESTINATION_PATTERN = re.compile(
    r"\b(?:trip|travel|visit)\s+(?:to\s+)?([A-Za-z][A-Za-z\s]{1,40}?)(?:\s+for\b|\s+under\b|\s+departing\b|[.,]|$)",
    re.IGNORECASE,
)
_BUDGET_PATTERN = re.compile(
    r"(?:under|budget(?:\s+of)?)\s*(?:₹|INR\s*)?([\d,]+)",
    re.IGNORECASE,
)
_DEPARTURE_PATTERN = re.compile(
    r"\bdeparting\s+from\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:[.,]|$)",
    re.IGNORECASE,
)
_TRIP_TYPE_PATTERN = re.compile(
    r"\b(leisure|business|family|adventure)\s+trip\b",
    re.IGNORECASE,
)
_PREFERENCE_PATTERN = re.compile(
    r"\b(?:prefer|preferences?:)\s*([^.]+)",
    re.IGNORECASE,
)
_DATE_RANGE_PATTERN = re.compile(
    r"\bfrom\s+([A-Za-z]+\s+\d{1,2})\s+to\s+([A-Za-z]+\s+\d{1,2})\b",
    re.IGNORECASE,
)


def _parse_budget_amount(raw_amount: str) -> Decimal:
    normalized = raw_amount.replace(",", "")
    return Decimal(normalized)


def _parse_preferences(text: str) -> list[str]:
    match = _PREFERENCE_PATTERN.search(text)
    if match is None:
        return []
    return [part.strip() for part in match.group(1).split(",") if part.strip()]


def extract_from_text(text: str, existing: TripRequest | None = None) -> TripRequest:
    """Parse trip requirements from text without inventing values."""
    request = existing.model_copy(deep=True) if existing is not None else TripRequest()

    duration_match = _DURATION_PATTERN.search(text)
    if duration_match is not None:
        request.duration_days = int(duration_match.group(1))

    travelers_match = _TRAVELERS_PATTERN.search(text)
    if travelers_match is not None:
        request.travelers = int(travelers_match.group(1))

    destination_match = _DESTINATION_PATTERN.search(text)
    if destination_match is not None:
        request.destination = destination_match.group(1).strip().title()

    budget_match = _BUDGET_PATTERN.search(text)
    if budget_match is not None:
        request.budget_amount = _parse_budget_amount(budget_match.group(1))
        request.budget_currency = "INR"

    departure_match = _DEPARTURE_PATTERN.search(text)
    if departure_match is not None:
        request.departure_city = departure_match.group(1).strip().title()

    trip_type_match = _TRIP_TYPE_PATTERN.search(text)
    if trip_type_match is not None:
        request.trip_type = TripType(trip_type_match.group(1).lower())

    preferences = _parse_preferences(text)
    if preferences:
        request.preferences = preferences

    return request
