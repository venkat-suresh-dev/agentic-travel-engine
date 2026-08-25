"""Phase 2 integration hardening tests for the agent lifecycle."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from app.agent.service import TripPlannerAgentService
from app.api.deps import get_agent_run_service, get_auth_verifier
from app.auth.types import AuthenticatedIdentity
from app.db.session import get_db
from app.main import create_app
from app.services.agent_runs import AgentRunRegistry, AgentRunService
from app.services.users import resolve_or_create_user
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fakes.llm import FakeLLMAdapter
from tests.test_auth import FakeAuthVerifier

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."
BUDGET_CLARIFICATION = "My budget is under ₹1,50,000."
RELAXED_PACE_CLARIFICATION = "We prefer a relaxed pace."


@pytest.fixture
def checkpointer() -> InMemorySaver:
    return InMemorySaver()


@pytest.fixture
def fake_adapter() -> FakeLLMAdapter:
    return FakeLLMAdapter.from_stub()


@pytest.fixture
def agent_service(
    fake_adapter: FakeLLMAdapter,
    checkpointer: InMemorySaver,
) -> TripPlannerAgentService:
    return TripPlannerAgentService(
        llm_adapter=fake_adapter,
        checkpointer=checkpointer,
    )


@pytest.fixture
def agent_run_service(
    agent_service: TripPlannerAgentService,
) -> AgentRunService:
    return AgentRunService(agent_service, AgentRunRegistry())


@pytest.fixture
def hardening_app(
    db_session: AsyncSession,
    agent_run_service: AgentRunService,
) -> Generator[FastAPI]:
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_run_service] = lambda: agent_run_service
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hardening_client(hardening_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=hardening_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _setup_user(
    hardening_app: FastAPI,
    db_session: AsyncSession,
    *,
    external_auth_id: str,
    email: str,
) -> dict[str, str]:
    identity = AuthenticatedIdentity(
        external_auth_id=external_auth_id,
        email=email,
        display_name="Hardening User",
    )
    await resolve_or_create_user(db_session, identity)
    hardening_app.dependency_overrides[get_auth_verifier] = lambda: FakeAuthVerifier(
        identity
    )
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_run_id_matches_graph_thread_id(
    hardening_app: FastAPI,
    hardening_client: AsyncClient,
    db_session: AsyncSession,
    agent_service: TripPlannerAgentService,
) -> None:
    headers = await _setup_user(
        hardening_app,
        db_session,
        external_auth_id="hardening-thread",
        email="thread@example.com",
    )

    response = await hardening_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = response.json()["run_id"]

    checkpointed = agent_service.get_state(run_id)

    assert response.status_code == 201
    assert checkpointed is not None
    assert checkpointed.thread_id == run_id


def test_resume_failure_preserves_checkpointed_requirements(
    checkpointer: InMemorySaver,
    fake_adapter: FakeLLMAdapter,
) -> None:
    registry = AgentRunRegistry()
    user_id = uuid4()
    service = AgentRunService(
        TripPlannerAgentService(
            llm_adapter=fake_adapter,
            checkpointer=checkpointer,
        ),
        registry,
    )
    initial = service.start_run(user_id, INCOMPLETE_REQUEST)

    assert initial.trip_request is not None
    assert initial.trip_request.destination == "Dubai"
    assert initial.trip_request.departure_city is None

    failing_service = AgentRunService(
        TripPlannerAgentService(
            llm_adapter=FakeLLMAdapter(should_fail=True),
            checkpointer=checkpointer,
        ),
        registry,
    )
    outcome = failing_service.resume_run(
        user_id,
        initial.run_id,
        BUDGET_CLARIFICATION,
    )

    assert outcome.status.value == "failed"
    assert outcome.trip_request is not None
    assert outcome.trip_request.destination == "Dubai"
    assert outcome.trip_request.travelers == 2
    assert outcome.trip_request.budget_amount is None
    assert outcome.trip_request.departure_city is None


@pytest.mark.asyncio
async def test_resume_failure_via_api_preserves_checkpointed_state(
    hardening_app: FastAPI,
    hardening_client: AsyncClient,
    db_session: AsyncSession,
    checkpointer: InMemorySaver,
    fake_adapter: FakeLLMAdapter,
) -> None:
    registry = AgentRunRegistry()
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        checkpointer=checkpointer,
    )
    hardening_app.dependency_overrides[get_agent_run_service] = lambda: AgentRunService(
        service,
        registry,
    )
    headers = await _setup_user(
        hardening_app,
        db_session,
        external_auth_id="hardening-resume-fail",
        email="resume-fail@example.com",
    )

    initial = await hardening_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]

    hardening_app.dependency_overrides[get_agent_run_service] = lambda: AgentRunService(
        TripPlannerAgentService(
            llm_adapter=FakeLLMAdapter(should_fail=True),
            checkpointer=checkpointer,
        ),
        registry,
    )

    failed = await hardening_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": BUDGET_CLARIFICATION},
        headers=headers,
    )

    body = failed.json()
    assert failed.status_code == 200
    assert body["status"] == "failed"
    assert body["trip_request"]["destination"] == "Dubai"
    assert body["trip_request"]["travelers"] == 2
    assert body["trip_request"]["budget_amount"] is None
    assert body["trip_request"]["departure_city"] is None
    assert "traceback" not in failed.text.lower()


@pytest.mark.asyncio
async def test_clarification_cannot_erase_existing_departure_city(
    hardening_app: FastAPI,
    hardening_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _setup_user(
        hardening_app,
        db_session,
        external_auth_id="hardening-no-erase",
        email="no-erase@example.com",
    )

    initial = await hardening_client.post(
        "/api/agent/runs",
        json={
            "message": (
                "Plan a 5-day trip to Dubai for 2 people departing from Mumbai."
            ),
        },
        headers=headers,
    )
    run_id = initial.json()["run_id"]

    clarified = await hardening_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": BUDGET_CLARIFICATION},
        headers=headers,
    )

    trip_request = clarified.json()["trip_request"]
    assert trip_request["destination"] == "Dubai"
    assert trip_request["duration_days"] == 5
    assert trip_request["travelers"] == 2
    assert trip_request["departure_city"] == "Mumbai"
    assert Decimal(trip_request["budget_amount"]) == Decimal("150000")


@pytest.mark.asyncio
async def test_unchanged_context_adds_relaxed_preference(
    hardening_app: FastAPI,
    hardening_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _setup_user(
        hardening_app,
        db_session,
        external_auth_id="hardening-relaxed",
        email="relaxed@example.com",
    )

    initial = await hardening_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]
    assert initial.json()["status"] == "complete"

    clarified = await hardening_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": RELAXED_PACE_CLARIFICATION},
        headers=headers,
    )

    trip_request = clarified.json()["trip_request"]
    assert trip_request["destination"] == "Dubai"
    assert trip_request["duration_days"] == 5
    assert trip_request["travelers"] == 2
    assert trip_request["departure_city"] == "Mumbai"
    assert Decimal(trip_request["budget_amount"]) == Decimal("150000")
    assert any(
        "relaxed pace" in preference for preference in trip_request["preferences"]
    )


def test_malformed_resume_output_does_not_corrupt_checkpoint(
    checkpointer: InMemorySaver,
    fake_adapter: FakeLLMAdapter,
) -> None:
    registry = AgentRunRegistry()
    user_id = uuid4()
    service = AgentRunService(
        TripPlannerAgentService(
            llm_adapter=fake_adapter,
            checkpointer=checkpointer,
        ),
        registry,
    )
    initial = service.start_run(user_id, INCOMPLETE_REQUEST)

    failing_service = AgentRunService(
        TripPlannerAgentService(
            llm_adapter=FakeLLMAdapter(
                malformed_payload={
                    "destination": "Dubai",
                    "start_date": "2026-12-10",
                    "end_date": "2026-12-01",
                }
            ),
            checkpointer=checkpointer,
        ),
        registry,
    )
    outcome = failing_service.resume_run(
        user_id,
        initial.run_id,
        BUDGET_CLARIFICATION,
    )

    assert outcome.status.value == "failed"
    planner = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        checkpointer=checkpointer,
    )
    checkpointed = planner.get_state(initial.run_id)
    assert checkpointed is not None
    assert checkpointed.trip_request is not None
    assert checkpointed.trip_request.destination == "Dubai"
    assert checkpointed.trip_request.budget_amount is None
