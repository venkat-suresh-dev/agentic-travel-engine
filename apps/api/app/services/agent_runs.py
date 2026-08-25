"""In-memory agent run registry and API-facing orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from uuid import UUID, uuid4

from app.agent.exceptions import RequirementExtractionError
from app.agent.service import TripPlannerAgentService, TripPlannerRunResult
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
from app.auth.exceptions import AuthorizationError, ResourceNotFoundError
from app.domain.trip_request import ClarificationRequest, TripRequest, ValidationResult
from app.itinerary.schemas import Itinerary
from app.services.conversation_mapper import (
    _valid_itinerary,
    build_budget_summary,
    build_critic_summary,
    build_modification_failure,
    build_operation_result,
    build_planning_failure,
    build_tool_availability,
    classify_resume_operation,
    infer_snapshot_operation_type,
    resolve_run_status,
)

AgentRunStatus = AgentRunStatusResponse


@dataclass(frozen=True, slots=True)
class AgentRunOutcome:
    """Normalized API result for starting or resuming an agent run."""

    status: AgentRunStatus
    run_id: str
    trip_request: TripRequest | None
    missing_fields: tuple[str, ...]
    clarification: ClarificationRequest | None
    error: str | None
    operation: OperationResultResponse
    itinerary: Itinerary | None
    budget: BudgetSummaryResponse | None
    critic: CriticSummaryResponse | None
    tool_availability: ToolAvailabilityResponse | None
    planning_failure: PlanningFailureResponse | None
    modification_failure: ModificationFailureResponse | None


class AgentRunRegistry:
    """Thread-safe in-memory mapping of run IDs to owning application users.

    This registry provides ownership checks only. Graph checkpoints are stored
    separately by LangGraph's checkpointer keyed by the same run ID.
    """

    def __init__(self) -> None:
        self._runs: dict[str, UUID] = {}
        self._lock = Lock()

    def register(self, run_id: str, user_id: UUID) -> None:
        with self._lock:
            self._runs[run_id] = user_id

    def get_owner(self, run_id: str) -> UUID | None:
        with self._lock:
            return self._runs.get(run_id)

    def exists(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._runs


class AgentRunService:
    """Expose trip planner graph execution through an API-safe boundary."""

    _FAILURE_MESSAGE = "Requirement extraction failed. Please try again."

    def __init__(
        self,
        agent_service: TripPlannerAgentService,
        registry: AgentRunRegistry,
    ) -> None:
        self._agent_service = agent_service
        self._registry = registry

    def start_run(self, user_id: UUID, message: str) -> AgentRunOutcome:
        """Start a new planning run for the authenticated user."""
        run_id = str(uuid4())
        self._registry.register(run_id, user_id)
        try:
            result = self._agent_service.start(message, thread_id=run_id)
        except RequirementExtractionError:
            return self._failed_outcome(
                run_id,
                operation_type=ConversationOperationType.INITIAL_PLAN,
            )
        return self._map_result(
            result,
            operation_type=ConversationOperationType.INITIAL_PLAN,
        )

    def resume_run(
        self,
        user_id: UUID,
        run_id: str,
        message: str,
    ) -> AgentRunOutcome:
        """Resume an existing planning run after clarification or modification."""
        self._assert_run_access(user_id, run_id)
        prior = self._agent_service.get_state(run_id)
        operation_type = classify_resume_operation(prior)
        try:
            result = self._agent_service.resume(run_id, message)
        except RequirementExtractionError:
            return self._failed_outcome(run_id, operation_type=operation_type)
        return self._map_result(result, operation_type=operation_type)

    def get_run(self, user_id: UUID, run_id: str) -> AgentRunOutcome:
        """Return the latest checkpointed state for an owned planning run."""
        self._assert_run_access(user_id, run_id)
        result = self._agent_service.get_state(run_id)
        if result is None:
            raise ResourceNotFoundError("Agent run not found")
        operation_type = infer_snapshot_operation_type(result)
        return self._map_result(result, operation_type=operation_type)

    def _assert_run_access(self, user_id: UUID, run_id: str) -> None:
        owner_id = self._registry.get_owner(run_id)
        if owner_id is None:
            raise ResourceNotFoundError("Agent run not found")
        if owner_id != user_id:
            raise AuthorizationError("Agent run belongs to another user")

    def _map_result(
        self,
        result: TripPlannerRunResult,
        *,
        operation_type: ConversationOperationType,
    ) -> AgentRunOutcome:
        missing_fields = self._missing_fields(result.validation)
        itinerary = _valid_itinerary(result)
        status = resolve_run_status(result, itinerary=itinerary)
        operation = build_operation_result(
            result,
            operation_type=operation_type,
            status=status,
            itinerary=itinerary,
        )
        planning_failure = build_planning_failure(result)
        modification_failure = build_modification_failure(result)
        error = self._resolve_error(
            status=status,
            planning_failure=planning_failure,
            modification_failure=modification_failure,
        )
        return AgentRunOutcome(
            status=status,
            run_id=result.thread_id,
            trip_request=result.trip_request,
            missing_fields=missing_fields,
            clarification=(
                result.clarification
                if status == AgentRunStatus.NEEDS_CLARIFICATION
                else None
            ),
            error=error,
            operation=operation,
            itinerary=itinerary,
            budget=build_budget_summary(result.budget_result),
            critic=build_critic_summary(result),
            tool_availability=build_tool_availability(result),
            planning_failure=planning_failure,
            modification_failure=modification_failure,
        )

    def _failed_outcome(
        self,
        run_id: str,
        *,
        operation_type: ConversationOperationType,
    ) -> AgentRunOutcome:
        checkpointed = self._agent_service.get_state(run_id)
        if checkpointed is None:
            operation = OperationResultResponse(
                operation_type=operation_type,
                status=AgentRunStatusResponse.FAILED,
                summary="Requirement extraction failed.",
            )
            return AgentRunOutcome(
                status=AgentRunStatus.FAILED,
                run_id=run_id,
                trip_request=None,
                missing_fields=(),
                clarification=None,
                error=self._FAILURE_MESSAGE,
                operation=operation,
                itinerary=None,
                budget=None,
                critic=None,
                tool_availability=None,
                planning_failure=None,
                modification_failure=None,
            )

        itinerary = _valid_itinerary(checkpointed)
        status = AgentRunStatus.FAILED
        operation = build_operation_result(
            checkpointed,
            operation_type=operation_type,
            status=status,
            itinerary=itinerary,
        )
        return AgentRunOutcome(
            status=status,
            run_id=run_id,
            trip_request=checkpointed.trip_request,
            missing_fields=self._missing_fields(checkpointed.validation),
            clarification=checkpointed.clarification,
            error=self._FAILURE_MESSAGE,
            operation=operation,
            itinerary=itinerary,
            budget=build_budget_summary(checkpointed.budget_result),
            critic=build_critic_summary(checkpointed),
            tool_availability=build_tool_availability(checkpointed),
            planning_failure=build_planning_failure(checkpointed),
            modification_failure=build_modification_failure(checkpointed),
        )

    @staticmethod
    def _resolve_error(
        *,
        status: AgentRunStatus,
        planning_failure: PlanningFailureResponse | None,
        modification_failure: ModificationFailureResponse | None,
    ) -> str | None:
        if status != AgentRunStatus.FAILED:
            return None
        if modification_failure is not None:
            return modification_failure.message
        if planning_failure is not None:
            return planning_failure.message
        return AgentRunService._FAILURE_MESSAGE

    @staticmethod
    def _missing_fields(validation: ValidationResult | None) -> tuple[str, ...]:
        if validation is None:
            return ()
        return tuple(validation.missing_fields)
