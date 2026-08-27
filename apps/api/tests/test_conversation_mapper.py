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
    build_budget_summary,
    build_modification_failure,
    build_operation_result,
    build_tool_availability,
    build_tool_execution_records,
    classify_resume_operation,
    infer_snapshot_operation_type,
    resolve_run_status,
)

from tests.itinerary.fixtures import example_budget_result, example_valid_itinerary


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


def test_build_tool_execution_records_uses_result_data_status() -> None:
    result = _minimal_result(
        status=GraphStatus.COMPLETE,
        state={
            "flight_search": {
                "source": "serpapi-google-flights",
                "data_status": "live",
                "offers": [],
            },
            "hotel_search": {
                "source": "stayingapi-sandbox",
                "data_status": "live",
                "hotels": [],
            },
            "tool_orchestration": [
                {
                    "tool_name": "search_flights",
                    "provider": "serpapi",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "completed_at": "2026-01-01T00:00:01+00:00",
                    "duration_ms": 120.0,
                    "status": "unavailable",
                    "error_message": None,
                },
                {
                    "tool_name": "search_hotels",
                    "provider": "stayingapi",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "completed_at": "2026-01-01T00:00:01+00:00",
                    "duration_ms": 90.0,
                    "status": "unavailable",
                    "error_message": None,
                },
            ],
        },
    )
    records = build_tool_execution_records(result)
    flights = next(item for item in records if item.tool_name == "search_flights")
    hotels = next(item for item in records if item.tool_name == "search_hotels")
    assert flights.status == "success"
    assert flights.data_mode == "live"
    assert hotels.status == "success"
    assert hotels.data_mode == "sandbox"

    availability = build_tool_availability(result)
    assert availability is not None
    assert availability.unavailable_tools == []


def test_build_budget_summary_includes_authoritative_categories() -> None:
    summary = build_budget_summary(example_budget_result())
    assert summary is not None
    assert summary.categories
    names = {line.category.value for line in summary.categories}
    assert "flight" in names
    assert "hotel" in names
    for line in summary.categories:
        if line.included_in_total:
            assert line.amount is not None
            assert line.data_kind.value != "unavailable"


def test_build_budget_summary_preserves_excluded_hotel_line() -> None:
    from decimal import Decimal

    from app.budget.schemas import (
        BudgetCategory,
        BudgetResult,
        CategoryTotal,
        PriceDataKind,
    )

    budget = BudgetResult(
        currency="INR",
        budget_amount=Decimal("150000"),
        total_cost=Decimal("100000"),
        remaining=Decimal("50000"),
        budget_exceeded=False,
        variance=Decimal("50000"),
        categories=[
            CategoryTotal(
                category=BudgetCategory.FLIGHT,
                amount=Decimal("50000"),
                currency="INR",
                source_amount=Decimal("50000"),
                source_currency="INR",
                is_estimate=False,
                basis="provider_lowest_offer",
                data_kind=PriceDataKind.LIVE,
                included_in_total=True,
            ),
            CategoryTotal(
                category=BudgetCategory.HOTEL,
                amount=None,
                currency="INR",
                source_amount=Decimal("2122"),
                source_currency="EUR",
                is_estimate=False,
                basis="provider_lowest_hotel",
                assumption=(
                    "Hotel cost not included in INR budget "
                    "because currency conversion is unavailable."
                ),
                data_kind=PriceDataKind.UNAVAILABLE,
                included_in_total=False,
            ),
        ],
        unavailable_categories=[BudgetCategory.HOTEL],
    )
    summary = build_budget_summary(budget)
    assert summary is not None
    hotel = next(line for line in summary.categories if line.category.value == "hotel")
    assert hotel.included_in_total is False
    assert hotel.source_amount == Decimal("2122")
    assert hotel.source_currency == "EUR"
    assert hotel.assumption is not None
    assert "conversion is unavailable" in hotel.assumption
