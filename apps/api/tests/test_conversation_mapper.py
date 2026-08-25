"""Unit tests for conversation state classification and API mapping."""

from __future__ import annotations

from app.agent.service import TripPlannerRunResult
from app.agent.state import AgentState, GraphStatus
from app.api.conversation_schemas import (
    AgentRunStatusResponse,
    ConversationOperationType,
)
from app.modification.schemas import ModificationFailure, ModificationStatus
from app.services.conversation_mapper import (
    build_modification_failure,
    build_operation_result,
    classify_resume_operation,
    infer_snapshot_operation_type,
    resolve_run_status,
)

from tests.itinerary.fixtures import example_valid_itinerary


def _minimal_result(
    *,
    status: GraphStatus,
    state: AgentState,
    planning_failed: bool = False,
) -> TripPlannerRunResult:
    return TripPlannerRunResult(
        thread_id="thread-1",
        status=status,
        trip_request=None,
        validation=None,
        clarification=None,
        weather_forecast=None,
        weather_tool_metadata=None,
        flight_search=None,
        flight_tool_metadata=None,
        hotel_search=None,
        hotel_tool_metadata=None,
        distance_matrix=None,
        distance_tool_metadata=None,
        restaurant_search=None,
        restaurant_tool_metadata=None,
        attraction_search=None,
        attraction_tool_metadata=None,
        currency_conversion=None,
        currency_tool_metadata=None,
        budget_result=None,
        itinerary_build_result=None,
        critic_result=None,
        planning_failed=planning_failed,
        aggregate_run_status=None,
        tool_orchestration_summary=None,
        state=state,
    )


def test_classify_resume_operation_awaiting_user_is_clarification() -> None:
    prior = _minimal_result(
        status=GraphStatus.AWAITING_USER,
        state={"status": GraphStatus.AWAITING_USER.value},
    )
    assert classify_resume_operation(prior) == ConversationOperationType.CLARIFICATION


def test_classify_resume_operation_completed_itinerary_is_modification() -> None:
    itinerary = example_valid_itinerary(duration_days=2)
    prior = _minimal_result(
        status=GraphStatus.COMPLETE,
        state={
            "status": GraphStatus.COMPLETE.value,
            "itinerary": itinerary.model_dump(mode="json"),
            "planning_failed": False,
        },
    )
    assert classify_resume_operation(prior) == ConversationOperationType.MODIFICATION


def test_classify_resume_operation_planning_failed_is_clarification() -> None:
    prior = _minimal_result(
        status=GraphStatus.COMPLETE,
        state={"status": GraphStatus.COMPLETE.value, "planning_failed": True},
        planning_failed=True,
    )
    assert classify_resume_operation(prior) == ConversationOperationType.CLARIFICATION


def test_resolve_run_status_maps_modification_failure_to_failed() -> None:
    itinerary = example_valid_itinerary(duration_days=2)
    result = _minimal_result(
        status=GraphStatus.COMPLETE,
        state={
            "status": GraphStatus.COMPLETE.value,
            "modification_status": ModificationStatus.FAILED.value,
            "modification_failure": ModificationFailure(
                message="could not apply change",
                preserved_itinerary=True,
            ).model_dump(mode="json"),
            "itinerary": itinerary.model_dump(mode="json"),
        },
    )
    assert (
        resolve_run_status(result, itinerary=itinerary) == AgentRunStatusResponse.FAILED
    )


def test_build_operation_result_marks_modification_failure_summary() -> None:
    itinerary = example_valid_itinerary(duration_days=2)
    result = _minimal_result(
        status=GraphStatus.COMPLETE,
        state={
            "modification_status": ModificationStatus.FAILED.value,
            "modification_failure": ModificationFailure(
                message="could not apply change",
                preserved_itinerary=True,
            ).model_dump(mode="json"),
            "modification_scope": {
                "affected_days": [2],
                "affected_item_ids": [],
                "affected_trip_fields": [],
                "requires_tool_refresh": False,
                "requires_budget_recompute": False,
                "requires_critic": True,
            },
        },
    )
    operation = build_operation_result(
        result,
        operation_type=ConversationOperationType.MODIFICATION,
        status=AgentRunStatusResponse.FAILED,
        itinerary=itinerary,
    )
    assert operation.operation_type == ConversationOperationType.MODIFICATION
    assert operation.status.value == "failed"
    assert operation.affected_days == [2]
    assert "could not be applied" in (operation.summary or "")


def test_infer_snapshot_operation_type_for_modification() -> None:
    itinerary = example_valid_itinerary(duration_days=2)
    result = _minimal_result(
        status=GraphStatus.COMPLETE,
        state={
            "modification_status": ModificationStatus.COMPLETE.value,
            "itinerary": itinerary.model_dump(mode="json"),
        },
    )
    assert (
        infer_snapshot_operation_type(result) == ConversationOperationType.MODIFICATION
    )


def test_build_modification_failure_from_state() -> None:
    result = _minimal_result(
        status=GraphStatus.COMPLETE,
        state={
            "modification_failure": ModificationFailure(
                message="provider refresh failed",
                issues=["hotels unavailable"],
                preserved_itinerary=True,
            ).model_dump(mode="json"),
        },
    )
    failure = build_modification_failure(result)
    assert failure is not None
    assert failure.preserved_itinerary is True
    assert failure.issues == ["hotels unavailable"]
