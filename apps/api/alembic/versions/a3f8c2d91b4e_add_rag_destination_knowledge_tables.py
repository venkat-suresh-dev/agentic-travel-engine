"""add rag destination knowledge tables

Revision ID: a3f8c2d91b4e
Revises: 95127f497d2e
Create Date: 2026-08-25 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "a3f8c2d91b4e"
down_revision: str | Sequence[str] | None = "95127f497d2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "rag_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("destination", sa.String(length=128), nullable=False),
        sa.Column("country", sa.String(length=128), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("last_verified", sa.Date(), nullable=False),
        sa.Column("document_version", sa.String(length=32), nullable=False),
        sa.Column("corpus_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_documents")),
        sa.UniqueConstraint(
            "document_id",
            "document_version",
            name="uq_rag_documents_id_version",
        ),
    )
    op.create_index(
        "ix_rag_documents_destination",
        "rag_documents",
        ["destination"],
        unique=False,
    )
    op.create_index(
        "ix_rag_documents_topic",
        "rag_documents",
        ["topic"],
        unique=False,
    )

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chunk_id", sa.String(length=160), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("rag_document_id", sa.Integer(), nullable=False),
        sa.Column("destination", sa.String(length=128), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("document_version", sa.String(length=32), nullable=False),
        sa.Column("last_verified", sa.Date(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["rag_document_id"],
            ["rag_documents.id"],
            name=op.f("fk_rag_chunks_rag_document_id_rag_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_chunks")),
        sa.UniqueConstraint("chunk_id", name="uq_rag_chunks_chunk_id"),
    )
    op.create_index(
        "ix_rag_chunks_destination",
        "rag_chunks",
        ["destination"],
        unique=False,
    )
    op.create_index(
        "ix_rag_chunks_topic",
        "rag_chunks",
        ["topic"],
        unique=False,
    )
    op.create_index(
        "ix_rag_chunks_document_id",
        "rag_chunks",
        ["document_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE INDEX ix_rag_chunks_search_text_fts
        ON rag_chunks
        USING gin (to_tsvector('english', search_text))
        """
    )
    op.execute(
        """
        CREATE INDEX ix_rag_chunks_embedding_hnsw
        ON rag_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_rag_chunks_embedding_hnsw", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_search_text_fts", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_document_id", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_topic", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_destination", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index("ix_rag_documents_topic", table_name="rag_documents")
    op.drop_index("ix_rag_documents_destination", table_name="rag_documents")
    op.drop_table("rag_documents")
    op.execute("DROP EXTENSION IF EXISTS vector")
