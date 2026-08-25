from __future__ import annotations

from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RagDocument(Base, TimestampMixin):
    """Curated destination knowledge document metadata."""

    __tablename__ = "rag_documents"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "document_version", name="uq_rag_documents_id_version"
        ),
        Index("ix_rag_documents_destination", "destination"),
        Index("ix_rag_documents_topic", "topic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str] = mapped_column(String(128), nullable=False)
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_verified: Mapped[date] = mapped_column(Date, nullable=False)
    document_version: Mapped[str] = mapped_column(String(32), nullable=False)
    corpus_version: Mapped[str] = mapped_column(String(32), nullable=False)

    chunks: Mapped[list[RagChunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class RagChunk(Base, TimestampMixin):
    """Searchable knowledge chunk with vector and lexical fields."""

    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("chunk_id", name="uq_rag_chunks_chunk_id"),
        Index("ix_rag_chunks_destination", "destination"),
        Index("ix_rag_chunks_topic", "topic"),
        Index("ix_rag_chunks_document_id", "document_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(160), nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rag_document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rag_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_version: Mapped[str] = mapped_column(String(32), nullable=False)
    last_verified: Mapped[date] = mapped_column(Date, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    document: Mapped[RagDocument] = relationship(back_populates="chunks")
