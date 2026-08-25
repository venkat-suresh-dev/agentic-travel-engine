"""Validate extracted trip requirements."""

from __future__ import annotations

from app.agent.state import AgentState, GraphStatus, trip_request_from_state
from app.domain.trip_request import (
    REQUIRED_SCHEDULE_FIELDS,
    REQUIRED_TRIP_FIELDS,
    TripRequest,
    ValidationResult,
)


def _missing_fields(trip_request: TripRequest) -> list[str]:
    missing: list[str] = []
    for field_name in REQUIRED_TRIP_FIELDS:
        if getattr(trip_request, field_name) is None:
            missing.append(field_name)

    has_schedule = any(
        getattr(trip_request, field_name) is not None
        for field_name in REQUIRED_SCHEDULE_FIELDS
    )
    if not has_schedule:
        missing.append("duration_days")

    return missing


def validate_requirements(state: AgentState) -> AgentState:
    """Check whether extracted requirements are complete."""
    trip_request = trip_request_from_state(state) or TripRequest()
    missing_fields = _missing_fields(trip_request)
    validation = ValidationResult(
        is_complete=not missing_fields,
        missing_fields=missing_fields,
    )

    status = (
        GraphStatus.COMPLETE.value
        if validation.is_complete
        else GraphStatus.AWAITING_USER.value
    )

    return {
        "validation": validation.model_dump(mode="json"),
        "status": status,
    }
