"""In-memory agent run registry and API-facing orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from uuid import UUID, uuid4

from app.agent.exceptions import RequirementExtractionError
from app.agent.service import TripPlannerAgentService, TripPlannerRunResult
from app.agent.state import GraphStatus
from app.auth.exceptions import AuthorizationError, ResourceNotFoundError
from app.domain.trip_request import ClarificationRequest, TripRequest, ValidationResult


class AgentRunStatus(StrEnum):
    """Public API lifecycle status for an agent run."""

    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AgentRunOutcome:
    """Normalized API result for starting or resuming an agent run."""

    status: AgentRunStatus
    run_id: str
    trip_request: TripRequest | None
    missing_fields: tuple[str, ...]
    clarification: ClarificationRequest | None
    error: str | None


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
            return self._failed_outcome(run_id)
        return self._map_result(result)

    def resume_run(
        self,
        user_id: UUID,
        run_id: str,
        message: str,
    ) -> AgentRunOutcome:
        """Resume an existing planning run after user clarification."""
        self._assert_run_access(user_id, run_id)
        try:
            result = self._agent_service.resume(run_id, message)
        except RequirementExtractionError:
            return self._failed_outcome(run_id)
        return self._map_result(result)

    def _assert_run_access(self, user_id: UUID, run_id: str) -> None:
        owner_id = self._registry.get_owner(run_id)
        if owner_id is None:
            raise ResourceNotFoundError("Agent run not found")
        if owner_id != user_id:
            raise AuthorizationError("Agent run belongs to another user")

    def _map_result(self, result: TripPlannerRunResult) -> AgentRunOutcome:
        missing_fields = self._missing_fields(result.validation)
        if result.status == GraphStatus.COMPLETE:
            return AgentRunOutcome(
                status=AgentRunStatus.COMPLETE,
                run_id=result.thread_id,
                trip_request=result.trip_request,
                missing_fields=missing_fields,
                clarification=None,
                error=None,
            )
        if result.status == GraphStatus.AWAITING_USER:
            return AgentRunOutcome(
                status=AgentRunStatus.NEEDS_CLARIFICATION,
                run_id=result.thread_id,
                trip_request=result.trip_request,
                missing_fields=missing_fields,
                clarification=result.clarification,
                error=None,
            )
        return AgentRunOutcome(
            status=AgentRunStatus.FAILED,
            run_id=result.thread_id,
            trip_request=result.trip_request,
            missing_fields=missing_fields,
            clarification=result.clarification,
            error=self._FAILURE_MESSAGE,
        )

    def _failed_outcome(self, run_id: str) -> AgentRunOutcome:
        checkpointed = self._agent_service.get_state(run_id)
        return AgentRunOutcome(
            status=AgentRunStatus.FAILED,
            run_id=run_id,
            trip_request=checkpointed.trip_request if checkpointed else None,
            missing_fields=self._missing_fields(
                checkpointed.validation if checkpointed else None
            ),
            clarification=checkpointed.clarification if checkpointed else None,
            error=self._FAILURE_MESSAGE,
        )

    @staticmethod
    def _missing_fields(validation: ValidationResult | None) -> tuple[str, ...]:
        if validation is None:
            return ()
        return tuple(validation.missing_fields)
