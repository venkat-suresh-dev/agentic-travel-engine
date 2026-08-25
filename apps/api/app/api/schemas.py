from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.trip_request import TripType
from app.services.agent_runs import AgentRunOutcome


class HealthResponse(BaseModel):
    status: str
    service: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_auth_id: str
    email: str
    display_name: str | None


class TripOwnershipResponse(BaseModel):
    trip_id: UUID
    owned: bool


class AgentRunStatusResponse(StrEnum):
    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"
    FAILED = "failed"


class AgentRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)


class AgentRunMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)


class TripRequestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    travelers: int | None = None
    budget_amount: Decimal | None = None
    budget_currency: str | None = None
    departure_city: str | None = None
    trip_type: TripType | None = None
    preferences: list[str] = Field(default_factory=list)


class ClarificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_fields: list[str]
    prompts: dict[str, str]
    message: str


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AgentRunStatusResponse
    run_id: str
    trip_request: TripRequestResponse | None = None
    missing_fields: list[str] = Field(default_factory=list)
    clarification: ClarificationResponse | None = None
    error: str | None = None


def trip_request_to_response(
    trip_request: object | None,
) -> TripRequestResponse | None:
    if trip_request is None:
        return None
    return TripRequestResponse.model_validate(trip_request, from_attributes=True)


def agent_run_outcome_to_response(outcome: AgentRunOutcome) -> AgentRunResponse:
    clarification = outcome.clarification
    return AgentRunResponse(
        status=AgentRunStatusResponse(outcome.status.value),
        run_id=outcome.run_id,
        trip_request=trip_request_to_response(outcome.trip_request),
        missing_fields=list(outcome.missing_fields),
        clarification=(
            ClarificationResponse(
                missing_fields=clarification.missing_fields,
                prompts=clarification.prompts,
                message=clarification.message,
            )
            if clarification is not None
            else None
        ),
        error=outcome.error,
    )
