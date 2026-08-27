"""Map graph execution results into API-safe conversation responses."""

from __future__ import annotations

from typing import Any, cast

from app.agent.orchestration.aggregate import (
    _TOOL_RESULT_KEYS,
    INDEPENDENT_TOOL_NAMES,
    _tool_execution_status,
)
from app.agent.orchestration.schemas import ToolExecutionStatus
from app.agent.service import TripPlannerRunResult
from app.agent.state import AgentState, GraphStatus
from app.api.conversation_schemas import (
    AgentRunStatusResponse,
    BudgetCategoryLineResponse,
    BudgetSummaryResponse,
    ConversationOperationType,
    CriticSummaryResponse,
    ModificationFailureResponse,
    OperationResultResponse,
    PlanningFailureResponse,
    ToolAvailabilityResponse,
    ToolExecutionRecordResponse,
)
from app.budget.schemas import BudgetResult
from app.itinerary.schemas import Itinerary
from app.modification.diff import change_facts
from app.modification.diff import changed_item_ids as diff_changed_item_ids
from app.modification.schemas import (
    ModificationFailure,
    ModificationScope,
    ModificationStatus,
    RefreshPlan,
)


def classify_resume_operation(
    prior: TripPlannerRunResult | None,
) -> ConversationOperationType:
    """Classify a follow-up message using persisted run state."""
    if prior is None:
        return ConversationOperationType.CLARIFICATION
    if prior.status == GraphStatus.AWAITING_USER:
        return ConversationOperationType.CLARIFICATION
    if prior.planning_failed:
        return ConversationOperationType.CLARIFICATION
    itinerary = _valid_itinerary(prior)
    if itinerary is not None:
        return ConversationOperationType.MODIFICATION
    return ConversationOperationType.CLARIFICATION


def infer_snapshot_operation_type(
    result: TripPlannerRunResult,
) -> ConversationOperationType:
    """Infer the latest completed operation type for read-only run snapshots."""
    modification_status = result.state.get("modification_status")
    if modification_status in {
        ModificationStatus.IN_PROGRESS.value,
        ModificationStatus.COMPLETE.value,
        ModificationStatus.FAILED.value,
    }:
        return ConversationOperationType.MODIFICATION
    if result.status == GraphStatus.AWAITING_USER:
        return ConversationOperationType.CLARIFICATION
    validation = result.validation
    if validation is not None and not validation.is_complete:
        return ConversationOperationType.CLARIFICATION
    if result.planning_failed and _valid_itinerary(result) is None:
        return ConversationOperationType.INITIAL_PLAN
    return ConversationOperationType.INITIAL_PLAN


def resolve_run_status(
    result: TripPlannerRunResult,
    *,
    itinerary: Itinerary | None,
) -> AgentRunStatusResponse:
    state = result.state
    modification_status = state.get("modification_status")
    if modification_status == ModificationStatus.FAILED.value:
        return AgentRunStatusResponse.FAILED
    if state.get("modification_failure") is not None:
        return AgentRunStatusResponse.FAILED
    if result.status == GraphStatus.AWAITING_USER:
        return AgentRunStatusResponse.NEEDS_CLARIFICATION
    if result.planning_failed and itinerary is None:
        return AgentRunStatusResponse.FAILED
    if result.status == GraphStatus.COMPLETE:
        return AgentRunStatusResponse.COMPLETE
    return AgentRunStatusResponse.FAILED


def build_operation_result(
    result: TripPlannerRunResult,
    *,
    operation_type: ConversationOperationType,
    status: AgentRunStatusResponse,
    itinerary: Itinerary | None,
) -> OperationResultResponse:
    state = result.state
    scope = _modification_scope(state)
    refresh_plan = _refresh_plan(state)
    refreshed = _refreshed_sources(refresh_plan)
    affected_days = scope.affected_days if scope is not None else []
    previous = _previous_itinerary(state)
    facts: list[str] = []
    item_ids = scope.affected_item_ids if scope is not None else []
    budget_changed = _budget_changed(scope, operation_type, status)
    if (
        operation_type == ConversationOperationType.MODIFICATION
        and previous is not None
        and itinerary is not None
        and status == AgentRunStatusResponse.COMPLETE
    ):
        item_ids = diff_changed_item_ids(previous, itinerary)
        facts = change_facts(previous, itinerary, affected_days=affected_days)
        budget_changed = previous.budget_total_cost != itinerary.budget_total_cost
    summary = _operation_summary(
        operation_type=operation_type,
        affected_days=affected_days,
        refreshed_sources=refreshed,
        status=status,
    )
    return OperationResultResponse(
        operation_type=operation_type,
        status=AgentRunStatusResponse(status.value),
        affected_days=affected_days,
        changed_item_ids=item_ids,
        refreshed_sources=refreshed,
        budget_changed=budget_changed,
        summary=summary,
        change_facts=facts,
    )


def build_budget_summary(budget: BudgetResult | None) -> BudgetSummaryResponse | None:
    if budget is None:
        return None
    # Include unavailable lines so the UI can explain exclusions (e.g. hotel FX).
    categories = [
        BudgetCategoryLineResponse(
            category=line.category,
            amount=line.amount,
            currency=line.currency,
            data_kind=line.data_kind,
            included_in_total=line.included_in_total,
            is_estimate=line.is_estimate,
            source_amount=line.source_amount,
            source_currency=line.source_currency,
            assumption=line.assumption,
        )
        for line in budget.categories
    ]
    return BudgetSummaryResponse(
        currency=budget.currency,
        budget_amount=budget.budget_amount,
        total_cost=budget.total_cost,
        remaining=budget.remaining,
        budget_exceeded=budget.budget_exceeded,
        variance=budget.variance,
        categories=categories,
    )


def build_critic_summary(result: TripPlannerRunResult) -> CriticSummaryResponse | None:
    critic = result.critic_result
    if critic is None:
        return None
    return CriticSummaryResponse(
        valid=critic.valid,
        issue_count=len(critic.issues),
        warning_count=len(critic.warnings),
        issues=[issue.message for issue in critic.issues],
        warnings=[warning.message for warning in critic.warnings],
    )


_TOOL_METADATA_KEYS: dict[str, str] = {
    "fetch_weather": "weather_tool_metadata",
    "search_flights": "flight_tool_metadata",
    "search_hotels": "hotel_tool_metadata",
    "get_distance_matrix": "distance_tool_metadata",
    "search_restaurants": "restaurant_tool_metadata",
    "search_attractions": "attraction_tool_metadata",
    "convert_currency": "currency_tool_metadata",
}

_TOOL_STATUS_TO_API: dict[ToolExecutionStatus, str] = {
    ToolExecutionStatus.SUCCESS: "success",
    ToolExecutionStatus.UNAVAILABLE: "unavailable",
    ToolExecutionStatus.ERROR: "error",
    ToolExecutionStatus.SKIPPED: "skipped",
}


def _provider_label(
    raw: dict[str, Any] | None, metadata: dict[str, Any] | None
) -> str | None:
    if isinstance(raw, dict):
        source = raw.get("source")
        if isinstance(source, str) and source:
            return source
    if isinstance(metadata, dict):
        provider = metadata.get("provider")
        if isinstance(provider, str) and provider:
            return provider
    return None


def _data_mode_from_result(
    raw: dict[str, Any] | None,
    *,
    provider: str | None,
) -> str:
    if not isinstance(raw, dict):
        return "unavailable"
    data_status = raw.get("data_status")
    if data_status is None:
        return "unavailable"
    mode = str(data_status)
    if provider and "sandbox" in provider.lower():
        return "sandbox"
    return mode


def build_tool_execution_records(
    result: TripPlannerRunResult,
) -> list[ToolExecutionRecordResponse]:
    """Build authoritative per-tool trace rows from graph state and orchestration."""
    summary = result.tool_orchestration_summary
    records_by_name = (
        {record.tool_name: record for record in summary.tool_records}
        if summary is not None
        else {}
    )
    tool_names = list(INDEPENDENT_TOOL_NAMES)
    if result.currency_conversion is not None or "convert_currency" in records_by_name:
        tool_names.append("convert_currency")

    rows: list[ToolExecutionRecordResponse] = []
    for tool_name in tool_names:
        result_key = _TOOL_RESULT_KEYS.get(tool_name)
        raw_result = (
            cast(dict[str, Any], result.state.get(result_key))
            if result_key is not None
            else None
        )
        metadata_key = _TOOL_METADATA_KEYS.get(tool_name)
        raw_metadata = (
            cast(dict[str, Any], result.state.get(metadata_key))
            if metadata_key is not None
            else None
        )
        orchestration = records_by_name.get(tool_name)
        if raw_result is None and orchestration is None:
            continue

        execution_status = _tool_execution_status(tool_name, result.state)
        provider = (
            orchestration.provider
            if orchestration is not None and orchestration.provider
            else _provider_label(raw_result, raw_metadata)
        )
        rows.append(
            ToolExecutionRecordResponse(
                tool_name=tool_name,
                status=_TOOL_STATUS_TO_API[execution_status],
                data_mode=_data_mode_from_result(raw_result, provider=provider),
                provider=provider,
                duration_ms=orchestration.duration_ms if orchestration else None,
            )
        )
    return rows


def build_tool_availability(
    result: TripPlannerRunResult,
) -> ToolAvailabilityResponse | None:
    summary = result.tool_orchestration_summary
    if summary is None and not any(
        result.state.get(key) for key in _TOOL_RESULT_KEYS.values()
    ):
        return None
    tools = build_tool_execution_records(result)
    unavailable = [
        record.tool_name
        for record in tools
        if record.status in {"unavailable", "error"}
    ]
    aggregate_status = (
        summary.aggregate_run_status.value
        if summary is not None
        else ("partial" if unavailable else "success")
    )
    return ToolAvailabilityResponse(
        aggregate_status=aggregate_status,
        unavailable_tools=unavailable,
        duration_ms=summary.duration_ms if summary else None,
        tools=tools,
    )


def build_planning_failure(
    result: TripPlannerRunResult,
) -> PlanningFailureResponse | None:
    raw = result.state.get("planning_failure")
    if raw is None or not result.planning_failed:
        return None
    if not isinstance(raw, dict):
        return None
    attempts_raw = raw.get("attempts")
    attempts = attempts_raw if isinstance(attempts_raw, int) else None
    return PlanningFailureResponse(
        message=str(raw.get("message", "trip planning failed")),
        attempts=attempts,
    )


def build_modification_failure(
    result: TripPlannerRunResult,
) -> ModificationFailureResponse | None:
    raw = result.state.get("modification_failure")
    if raw is None:
        return None
    failure = ModificationFailure.model_validate(raw)
    return ModificationFailureResponse(
        message=failure.message,
        issues=list(failure.issues),
        preserved_itinerary=failure.preserved_itinerary,
    )


def _valid_itinerary(result: TripPlannerRunResult) -> Itinerary | None:
    build_result = result.itinerary_build_result
    if (
        build_result is not None
        and build_result.success
        and build_result.itinerary is not None
    ):
        return build_result.itinerary
    raw = result.state.get("itinerary")
    if raw is None:
        return None
    return Itinerary.model_validate(raw)


def _modification_scope(state: AgentState) -> ModificationScope | None:
    raw = state.get("modification_scope")
    if raw is None:
        return None
    return ModificationScope.model_validate(raw)


def _previous_itinerary(state: AgentState) -> Itinerary | None:
    raw = state.get("previous_itinerary")
    if raw is None:
        return None
    return Itinerary.model_validate(raw)


def _refresh_plan(state: AgentState) -> RefreshPlan | None:
    raw = state.get("refresh_plan")
    if raw is None:
        return None
    return RefreshPlan.model_validate(raw)


def _refreshed_sources(plan: RefreshPlan | None) -> list[str]:
    if plan is None:
        return []
    sources: list[str] = []
    if plan.refresh_weather:
        sources.append("weather")
    if plan.refresh_flights:
        sources.append("flights")
    if plan.refresh_hotels:
        sources.append("hotels")
    if plan.refresh_places:
        sources.append("places")
    if plan.refresh_distance:
        sources.append("distance")
    if plan.refresh_currency:
        sources.append("currency")
    if plan.refresh_rag:
        sources.append("rag")
    return sources


def _budget_changed(
    scope: ModificationScope | None,
    operation_type: ConversationOperationType,
    status: AgentRunStatusResponse,
) -> bool:
    if operation_type != ConversationOperationType.MODIFICATION:
        return False
    if status != AgentRunStatusResponse.COMPLETE:
        return False
    return bool(scope and scope.requires_budget_recompute)


def _operation_summary(
    *,
    operation_type: ConversationOperationType,
    affected_days: list[int],
    refreshed_sources: list[str],
    status: AgentRunStatusResponse,
) -> str | None:
    if operation_type == ConversationOperationType.INITIAL_PLAN:
        if status == AgentRunStatusResponse.NEEDS_CLARIFICATION:
            return "Additional trip details are required."
        if status == AgentRunStatusResponse.COMPLETE:
            return "Initial itinerary created."
        return "Initial planning failed."
    if operation_type == ConversationOperationType.CLARIFICATION:
        if status == AgentRunStatusResponse.NEEDS_CLARIFICATION:
            return "More clarification is required."
        if status == AgentRunStatusResponse.COMPLETE:
            return "Clarification completed and itinerary created."
        return "Clarification could not complete planning."
    if status == AgentRunStatusResponse.FAILED:
        return (
            "The requested change could not be applied. "
            "Your previous itinerary is still intact."
        )
    if affected_days:
        days = ", ".join(str(day) for day in affected_days)
        refreshed = (
            f" Refreshed: {', '.join(refreshed_sources)}."
            if refreshed_sources
            else " No provider refresh required."
        )
        return f"Updated day(s) {days}.{refreshed}"
    return "Itinerary updated."
