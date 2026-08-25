"""Shared pytest fixtures for database tests."""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer

pytest_plugins = [
    "tests.fakes.weather",
    "tests.fakes.flights",
    "tests.fakes.hotels",
    "tests.fakes.distance",
    "tests.fakes.places",
    "tests.fakes.llm_fixtures",
]


def _to_async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    raise ValueError(f"Unsupported database URL: {url}")


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    with PostgresContainer("postgres:18.6-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def database_url(postgres_container: PostgresContainer) -> str:
    return _to_async_database_url(postgres_container.get_connection_url())


@pytest.fixture(scope="session")
def migrated_database_url(database_url: str) -> str:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")
    return database_url


@pytest_asyncio.fixture
async def db_engine(migrated_database_url: str) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(migrated_database_url, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
