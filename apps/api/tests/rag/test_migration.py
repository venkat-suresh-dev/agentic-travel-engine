"""Alembic migration tests for RAG tables."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def test_rag_migration_upgrade_downgrade_upgrade(migrated_database_url: str) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", migrated_database_url)

    command.downgrade(alembic_cfg, "95127f497d2e")
    command.upgrade(alembic_cfg, "head")


async def test_pgvector_extension_and_tables_exist(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        extension = await connection.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        assert extension.scalar_one() is True

        tables = await connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('rag_documents', 'rag_chunks')
                ORDER BY table_name
                """
            )
        )
        assert [row[0] for row in tables.fetchall()] == ["rag_chunks", "rag_documents"]
