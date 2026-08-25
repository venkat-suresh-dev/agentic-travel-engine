"""Authentication and ownership tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from app.api.deps import get_auth_verifier
from app.auth.exceptions import AuthenticationError
from app.auth.types import AuthenticatedIdentity
from app.db.models.trip import Trip
from app.db.models.user import User
from app.db.session import get_db
from app.main import create_app
from app.services.users import resolve_or_create_user
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class FakeAuthVerifier:
    def __init__(
        self,
        identity: AuthenticatedIdentity | None = None,
        *,
        error: AuthenticationError | None = None,
    ) -> None:
        self.identity = identity
        self.error = error

    async def verify_request(self, _request: object) -> AuthenticatedIdentity:
        if self.error is not None:
            raise self.error
        if self.identity is None:
            raise AuthenticationError("missing authentication")
        return self.identity


@pytest.fixture
def auth_app(db_session: AsyncSession) -> Generator[FastAPI]:
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(auth_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _set_verifier(
    auth_app: FastAPI,
    identity: AuthenticatedIdentity | None = None,
    *,
    error: AuthenticationError | None = None,
) -> None:
    auth_app.dependency_overrides[get_auth_verifier] = lambda: FakeAuthVerifier(
        identity,
        error=error,
    )


@pytest.mark.asyncio
async def test_auth_me_requires_authentication(
    auth_app: FastAPI,
    auth_client: AsyncClient,
) -> None:
    _set_verifier(auth_app, error=AuthenticationError("missing token"))

    response = await auth_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing token"


@pytest.mark.asyncio
async def test_auth_me_rejects_invalid_authentication(
    auth_app: FastAPI,
    auth_client: AsyncClient,
) -> None:
    _set_verifier(auth_app, error=AuthenticationError("token-invalid"))

    response = await auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "token-invalid"


@pytest.mark.asyncio
async def test_resolve_or_create_user_creates_local_user(
    db_session: AsyncSession,
) -> None:
    identity = AuthenticatedIdentity(
        external_auth_id="user_new_clerk",
        email="new.user@example.com",
        display_name="New User",
    )

    user = await resolve_or_create_user(db_session, identity)

    assert user.external_auth_id == "user_new_clerk"
    assert user.email == "new.user@example.com"
    assert user.display_name == "New User"


@pytest.mark.asyncio
async def test_resolve_or_create_user_reuses_existing_user(
    db_session: AsyncSession,
) -> None:
    identity = AuthenticatedIdentity(
        external_auth_id="user_existing_clerk",
        email="existing.user@example.com",
    )

    first_user = await resolve_or_create_user(db_session, identity)
    second_user = await resolve_or_create_user(db_session, identity)

    assert first_user.id == second_user.id


@pytest.mark.asyncio
async def test_resolve_or_create_user_prevents_duplicates_on_race(
    db_engine: AsyncEngine,
) -> None:
    identity = AuthenticatedIdentity(
        external_auth_id="user_race_clerk",
        email="race.user@example.com",
    )
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def create_user() -> User:
        async with session_factory() as session:
            return await resolve_or_create_user(session, identity)

    users = await asyncio.gather(create_user(), create_user())

    assert users[0].id == users[1].id
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.external_auth_id == "user_race_clerk")
        )
    assert count == 1


@pytest_asyncio.fixture
async def existing_user(db_session: AsyncSession) -> User:
    user = User(
        external_auth_id="user_existing_me",
        email="me.user@example.com",
        display_name="Me User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_auth_me_returns_existing_user(
    auth_app: FastAPI,
    auth_client: AsyncClient,
    existing_user: User,
) -> None:
    _set_verifier(
        auth_app,
        AuthenticatedIdentity(
            external_auth_id="user_existing_me",
            email="different@example.com",
        ),
    )

    response = await auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(existing_user.id)
    assert body["external_auth_id"] == "user_existing_me"
    assert body["email"] == "me.user@example.com"


@pytest.mark.asyncio
async def test_auth_me_creates_user_on_first_login(
    auth_app: FastAPI,
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _set_verifier(
        auth_app,
        AuthenticatedIdentity(
            external_auth_id="user_first_login",
            email="first.login@example.com",
            display_name="First Login",
        ),
    )

    response = await auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["external_auth_id"] == "user_first_login"
    assert body["email"] == "first.login@example.com"

    created_user = await db_session.scalar(
        select(User).where(User.external_auth_id == "user_first_login")
    )
    assert created_user is not None


@pytest_asyncio.fixture
async def owned_trip(db_session: AsyncSession) -> tuple[User, Trip]:
    owner = User(
        external_auth_id="owner_clerk",
        email="owner@example.com",
    )
    trip = Trip(user=owner, title="Ownership Trip", destination="Paris")
    db_session.add(owner)
    await db_session.commit()
    await db_session.refresh(owner)
    await db_session.refresh(trip)
    return owner, trip


@pytest.mark.asyncio
async def test_trip_ownership_succeeds_for_owner(
    auth_app: FastAPI,
    auth_client: AsyncClient,
    owned_trip: tuple[User, Trip],
) -> None:
    _, trip = owned_trip
    _set_verifier(
        auth_app,
        AuthenticatedIdentity(
            external_auth_id="owner_clerk", email="owner@example.com"
        ),
    )

    response = await auth_client.get(
        f"/api/trips/{trip.id}/ownership",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"trip_id": str(trip.id), "owned": True}


@pytest_asyncio.fixture
async def foreign_trip(db_session: AsyncSession) -> tuple[User, User, Trip]:
    owner = User(
        external_auth_id="real_owner",
        email="real.owner@example.com",
    )
    other_user = User(
        external_auth_id="other_user",
        email="other.user@example.com",
    )
    trip = Trip(user=owner, title="Foreign Trip", destination="Rome")
    db_session.add_all([owner, other_user])
    await db_session.commit()
    await db_session.refresh(trip)
    return owner, other_user, trip


@pytest.mark.asyncio
async def test_trip_ownership_fails_for_non_owner(
    auth_app: FastAPI,
    auth_client: AsyncClient,
    foreign_trip: tuple[User, User, Trip],
) -> None:
    _, _, trip = foreign_trip
    _set_verifier(
        auth_app,
        AuthenticatedIdentity(
            external_auth_id="other_user",
            email="other.user@example.com",
        ),
    )

    response = await auth_client.get(
        f"/api/trips/{trip.id}/ownership",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403
    assert "does not belong" in response.json()["detail"]


@pytest.mark.asyncio
async def test_trip_ownership_returns_not_found_for_missing_trip(
    auth_app: FastAPI,
    auth_client: AsyncClient,
) -> None:
    _set_verifier(
        auth_app,
        AuthenticatedIdentity(
            external_auth_id="lonely_user", email="lonely@example.com"
        ),
    )

    missing_trip_id = uuid4()
    response = await auth_client.get(
        f"/api/trips/{missing_trip_id}/ownership",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"
