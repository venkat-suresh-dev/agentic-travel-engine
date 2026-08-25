"""Map validator issue codes to critic issue codes."""

from __future__ import annotations

from app.itinerary.critic.schemas import CriticIssueCode, CriticIssueSeverity
from app.itinerary.schemas import ItineraryValidationIssue

_VALIDATOR_CODE_MAP: dict[str, CriticIssueCode] = {
    "day_count_mismatch": CriticIssueCode.DAY_COUNT_MISMATCH,
    "missing_duration_days": CriticIssueCode.DAY_COUNT_MISMATCH,
    "invalid_day_sequence": CriticIssueCode.MISSING_DAY,
    "time_overlap": CriticIssueCode.TIME_OVERLAP,
    "travel_buffer_violation": CriticIssueCode.TRAVEL_BUFFER_VIOLATION,
    "unknown_attraction_source": CriticIssueCode.UNKNOWN_SOURCE,
    "unknown_restaurant_source": CriticIssueCode.UNKNOWN_SOURCE,
    "unknown_flight_source": CriticIssueCode.UNKNOWN_SOURCE,
    "subtotal_mismatch": CriticIssueCode.DAILY_SUBTOTAL_MISMATCH,
    "missing_meal": CriticIssueCode.MISSING_MEAL,
    "invalid_time_range": CriticIssueCode.INVALID_TIME_RANGE,
    "unavailable_cost_not_zero": CriticIssueCode.INVALID_COST,
    "composition_failed": CriticIssueCode.UNSUPPORTED_ITEM,
    "missing_context": CriticIssueCode.UNSUPPORTED_ITEM,
}

_RETRYABLE_CODES = frozenset(
    {
        CriticIssueCode.DAY_COUNT_MISMATCH,
        CriticIssueCode.TIME_OVERLAP,
        CriticIssueCode.TRAVEL_BUFFER_VIOLATION,
        CriticIssueCode.UNKNOWN_SOURCE,
        CriticIssueCode.MISSING_MEAL,
        CriticIssueCode.MISSING_DAY,
        CriticIssueCode.WEATHER_RULE_VIOLATION,
        CriticIssueCode.UNSUPPORTED_ITEM,
    }
)


def map_validator_issue(issue: ItineraryValidationIssue) -> CriticIssueCode:
    mapped = _VALIDATOR_CODE_MAP.get(issue.code)
    if mapped is not None:
        return mapped
    normalized = issue.code.upper()
    try:
        return CriticIssueCode(normalized)
    except ValueError:
        return CriticIssueCode.UNSUPPORTED_ITEM


def is_retryable(code: CriticIssueCode) -> bool:
    return code in _RETRYABLE_CODES


def default_severity(code: CriticIssueCode) -> CriticIssueSeverity:
    if code == CriticIssueCode.BUDGET_EXCEEDED:
        return CriticIssueSeverity.WARNING
    return CriticIssueSeverity.ERROR
