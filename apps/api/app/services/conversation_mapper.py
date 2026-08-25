"""Map graph execution results into API-safe conversation responses."""

from __future__ import annotations

from app.agent.orchestration.schemas import ToolExecutionStatus
from app.agent.service import TripPlannerRunResult
from app.agent.state import AgentState, GraphStatus
from app.api.conversation_schemas import (
    AgentRunStatusResponse,
    BudgetSummaryResponse,
    ConversationOperationType,
    CriticSummaryResponse,
    ModificationFailureResponse,
    OperationResultResponse,
    PlanningFailureResponse,
    ToolAvailabilityResponse,
)
from app.budget.schemas import BudgetResult
from app.itinerary.schemas import Itinerary
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
        changed_item_ids=scope.affected_item_ids if scope is not None else [],
        refreshed_sources=refreshed,
        budget_changed=_budget_changed(scope, operation_type, status),
        summary=summary,
    )


def build_budget_summary(budget: BudgetResult | None) -> BudgetSummaryResponse | None:
    if budget is None:
        return None
    return BudgetSummaryResponse(
        currency=budget.currency,
        budget_amount=budget.budget_amount,
        total_cost=budget.total_cost,
        remaining=budget.remaining,
        budget_exceeded=budget.budget_exceeded,
        variance=budget.variance,
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


def build_tool_availability(
    result: TripPlannerRunResult,
) -> ToolAvailabilityResponse | None:
    summary = result.tool_orchestration_summary
    if summary is None:
        return None
    unavailable = [
        record.tool_name
        for record in summary.tool_records
        if record.status in {ToolExecutionStatus.UNAVAILABLE, ToolExecutionStatus.ERROR}
    ]
    return ToolAvailabilityResponse(
        aggregate_status=summary.aggregate_run_status.value,
        unavailable_tools=unavailable,
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
