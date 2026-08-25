"""Integration tests for the agent planning API."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from decimal import Decimal

import pytest
import pytest_asyncio
from app.agent.service import TripPlannerAgentService
from app.api.deps import get_agent_run_service, get_auth_verifier
from app.auth.exceptions import AuthenticationError
from app.auth.types import AuthenticatedIdentity
from app.db.session import get_db
from app.main import create_app
from app.services.agent_runs import AgentRunRegistry, AgentRunService
from app.services.users import resolve_or_create_user
from app.tools.attractions import AttractionTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fakes.distance_providers import FakeLocationResolver
from tests.fakes.flights_providers import FakeAirportCodeResolver
from tests.fakes.hotels_providers import FakeCityCodeResolver
from tests.fakes.llm import FakeLLMAdapter
from tests.test_auth import FakeAuthVerifier

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."
FULL_CONTEXT_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
BUDGET_CLARIFICATION = "My budget is under ₹1,50,000."
DEPARTURE_CLARIFICATION = "We are departing from Mumbai."
FULL_CLARIFICATION = "My budget is under ₹1,50,000 and I am departing from Mumbai."


@pytest.fixture
def agent_registry() -> AgentRunRegistry:
    return AgentRunRegistry()


@pytest.fixture
def agent_service(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_restaurant_tool: RestaurantTool,
    fake_attraction_tool: AttractionTool,
) -> TripPlannerAgentService:
    return TripPlannerAgentService(
        llm_adapter=fake_adapter,
        checkpointer=InMemorySaver(),
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=fake_restaurant_tool,
        attraction_tool=fake_attraction_tool,
    )


@pytest.fixture
def agent_run_service(
    agent_service: TripPlannerAgentService,
    agent_registry: AgentRunRegistry,
) -> AgentRunService:
    return AgentRunService(agent_service, agent_registry)


@pytest.fixture
def fake_adapter() -> FakeLLMAdapter:
    return FakeLLMAdapter.from_stub()


@pytest.fixture
def agent_app(
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
async def agent_client(agent_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=agent_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _set_verifier(
    agent_app: FastAPI,
    identity: AuthenticatedIdentity | None = None,
    *,
    error: AuthenticationError | None = None,
) -> None:
    agent_app.dependency_overrides[get_auth_verifier] = lambda: FakeAuthVerifier(
        identity,
        error=error,
    )


@pytest.mark.asyncio
async def test_create_agent_run_requires_authentication(
    agent_app: FastAPI,
    agent_client: AsyncClient,
) -> None:
    _set_verifier(agent_app, error=AuthenticationError("missing token"))

    response = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_complete_request_finishes_immediately(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-complete",
            email="complete@example.com",
            display_name="Complete User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-complete",
            email="complete@example.com",
            display_name="Complete User",
        ),
    )

    response = await agent_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "complete"
    assert body["run_id"]
    assert body["trip_request"]["destination"] == "Dubai"
    assert body["trip_request"]["travelers"] == 2
    assert body["trip_request"]["budget_amount"] == "150000"
    assert body["missing_fields"] == []
    assert body["clarification"] is None
    assert body["error"] is None


@pytest.mark.asyncio
async def test_incomplete_request_returns_needs_clarification(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-incomplete",
            email="incomplete@example.com",
            display_name="Incomplete User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-incomplete",
            email="incomplete@example.com",
            display_name="Incomplete User",
        ),
    )

    response = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["trip_request"]["destination"] == "Dubai"
    assert body["trip_request"]["travelers"] == 2
    assert body["trip_request"]["budget_amount"] is None
    assert body["trip_request"]["departure_city"] is None
    assert "budget_amount" in body["missing_fields"]
    assert "departure_city" in body["missing_fields"]
    assert body["clarification"]["missing_fields"] == body["missing_fields"]


@pytest.mark.asyncio
async def test_clarification_resumes_existing_run(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-resume",
            email="resume@example.com",
            display_name="Resume User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-resume",
            email="resume@example.com",
            display_name="Resume User",
        ),
    )
    headers = {"Authorization": "Bearer test-token"}

    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]

    resumed = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": FULL_CLARIFICATION},
        headers=headers,
    )

    assert resumed.status_code == 200
    body = resumed.json()
    assert body["status"] == "complete"
    assert body["run_id"] == run_id
    assert body["trip_request"]["destination"] == "Dubai"
    assert body["trip_request"]["travelers"] == 2
    assert body["trip_request"]["duration_days"] == 5
    assert body["trip_request"]["budget_amount"] == "150000"
    assert body["trip_request"]["departure_city"] == "Mumbai"


@pytest.mark.asyncio
async def test_clarification_supplies_only_missing_fields(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-partial",
            email="partial@example.com",
            display_name="Partial User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-partial",
            email="partial@example.com",
            display_name="Partial User",
        ),
    )
    headers = {"Authorization": "Bearer test-token"}

    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]

    partial = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": BUDGET_CLARIFICATION},
        headers=headers,
    )

    assert partial.status_code == 200
    body = partial.json()
    assert body["status"] == "needs_clarification"
    assert body["trip_request"]["destination"] == "Dubai"
    assert body["trip_request"]["travelers"] == 2
    assert body["trip_request"]["budget_amount"] == "150000"
    assert body["missing_fields"] == ["departure_city"]


@pytest.mark.asyncio
async def test_multiple_clarification_turns_are_supported(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-multi",
            email="multi@example.com",
            display_name="Multi User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-multi",
            email="multi@example.com",
            display_name="Multi User",
        ),
    )
    headers = {"Authorization": "Bearer test-token"}

    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]

    first = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": BUDGET_CLARIFICATION},
        headers=headers,
    )
    assert first.json()["status"] == "needs_clarification"

    second = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": DEPARTURE_CLARIFICATION},
        headers=headers,
    )
    assert second.json()["status"] == "complete"
    assert second.json()["trip_request"]["departure_city"] == "Mumbai"


@pytest.mark.asyncio
async def test_clarification_preserves_existing_values_and_adds_preferences(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-context",
            email="context@example.com",
            display_name="Context User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-context",
            email="context@example.com",
            display_name="Context User",
        ),
    )
    headers = {"Authorization": "Bearer test-token"}

    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": FULL_CONTEXT_REQUEST},
        headers=headers,
    )
    assert initial.json()["status"] == "complete"
    run_id = initial.json()["run_id"]

    resumed = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": "We want a relaxed pace."},
        headers=headers,
    )

    assert resumed.status_code == 200
    body = resumed.json()
    assert body["status"] == "complete"
    trip_request = body["trip_request"]
    assert trip_request["destination"] == "Dubai"
    assert trip_request["duration_days"] == 5
    assert trip_request["travelers"] == 2
    assert trip_request["departure_city"] == "Mumbai"
    assert trip_request["budget_amount"] == "150000"
    assert "relaxed pace" in trip_request["preferences"]


@pytest.mark.asyncio
async def test_clarification_does_not_overwrite_unrelated_values(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-overwrite",
            email="overwrite@example.com",
            display_name="Overwrite User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-overwrite",
            email="overwrite@example.com",
            display_name="Overwrite User",
        ),
    )
    headers = {"Authorization": "Bearer test-token"}

    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]

    resumed = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": FULL_CLARIFICATION},
        headers=headers,
    )

    trip_request = resumed.json()["trip_request"]
    assert trip_request["destination"] == "Dubai"
    assert trip_request["duration_days"] == 5
    assert trip_request["travelers"] == 2
    assert Decimal(trip_request["budget_amount"]) == Decimal("150000")
    assert trip_request["departure_city"] == "Mumbai"


@pytest.mark.asyncio
async def test_invalid_run_id_is_rejected(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-invalid",
            email="invalid@example.com",
            display_name="Invalid User",
        ),
    )
    _set_verifier(
        agent_app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-invalid",
            email="invalid@example.com",
            display_name="Invalid User",
        ),
    )

    response = await agent_client.post(
        "/api/agent/runs/not-a-real-run/messages",
        json={"message": BUDGET_CLARIFICATION},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent run not found"


@pytest.mark.asyncio
async def test_another_user_cannot_resume_run(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner = AuthenticatedIdentity(
        external_auth_id="agent-user-owner",
        email="agent-owner@example.com",
        display_name="Owner User",
    )
    other = AuthenticatedIdentity(
        external_auth_id="agent-user-other",
        email="other@example.com",
        display_name="Other User",
    )
    await resolve_or_create_user(db_session, owner)
    await resolve_or_create_user(db_session, other)

    _set_verifier(agent_app, owner)
    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers={"Authorization": "Bearer owner-token"},
    )
    run_id = initial.json()["run_id"]

    _set_verifier(agent_app, other)
    response = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": BUDGET_CLARIFICATION},
        headers={"Authorization": "Bearer other-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Agent run belongs to another user"


@pytest.mark.asyncio
async def test_graph_failure_returns_controlled_response(
    db_session: AsyncSession,
) -> None:
    failing_adapter = FakeLLMAdapter(should_fail=True)
    registry = AgentRunRegistry()
    service = AgentRunService(
        TripPlannerAgentService(
            llm_adapter=failing_adapter,
            checkpointer=InMemorySaver(),
        ),
        registry,
    )
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_run_service] = lambda: service

    await resolve_or_create_user(
        db_session,
        AuthenticatedIdentity(
            external_auth_id="agent-user-failure",
            email="failure@example.com",
            display_name="Failure User",
        ),
    )
    _set_verifier(
        app,
        AuthenticatedIdentity(
            external_auth_id="agent-user-failure",
            email="failure@example.com",
            display_name="Failure User",
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent/runs",
            json={"message": INCOMPLETE_REQUEST},
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"] == "Requirement extraction failed. Please try again."
    assert "traceback" not in response.text.lower()
    assert "api key" not in response.text.lower()

    app.dependency_overrides.clear()
