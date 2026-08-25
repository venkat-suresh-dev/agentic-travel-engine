"""RAG ingestion pipeline tests."""

from __future__ import annotations

import pytest
from app.db.models.rag import RagChunk, RagDocument
from app.rag.chunking import build_chunk_id, chunk_document
from app.rag.embeddings.fake import FakeEmbeddingProvider
from app.rag.ingestion.pipeline import RagIngestionPipeline
from app.rag.ingestion.validator import CorpusValidationError, validate_document
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.rag.conftest import TEST_CORPUS_PATH, sample_document


async def test_valid_document_ingestion(
    db_session: AsyncSession,
    fake_embedding_provider: FakeEmbeddingProvider,
) -> None:
    pipeline = RagIngestionPipeline(
        session=db_session,
        embedding_provider=fake_embedding_provider,
    )
    report = await pipeline.ingest_corpus(TEST_CORPUS_PATH)

    assert report.documents_processed >= 7
    assert report.chunks_written > 0
    assert report.corpus_version == "v1"

    documents = (await db_session.execute(select(RagDocument))).scalars().all()
    chunks = (await db_session.execute(select(RagChunk))).scalars().all()
    assert len(documents) >= 7
    assert len(chunks) == report.chunks_written


def test_metadata_validation_rejects_invalid_source_url() -> None:
    document = sample_document().model_copy(update={"source_url": "not-a-url"})
    with pytest.raises(CorpusValidationError):
        validate_document(document)


def test_deterministic_chunk_ids() -> None:
    document = sample_document()
    chunks = chunk_document(document, target_tokens=400)
    assert chunks
    assert chunks[0].chunk_id == build_chunk_id(document.id, document.version, 0)


async def test_duplicate_ingestion_is_idempotent(
    db_session: AsyncSession,
    fake_embedding_provider: FakeEmbeddingProvider,
) -> None:
    pipeline = RagIngestionPipeline(
        session=db_session,
        embedding_provider=fake_embedding_provider,
    )
    first = await pipeline.ingest_corpus(TEST_CORPUS_PATH)
    second = await pipeline.ingest_corpus(TEST_CORPUS_PATH)

    chunk_count = await db_session.scalar(select(func.count()).select_from(RagChunk))
    document_count = await db_session.scalar(
        select(func.count()).select_from(RagDocument)
    )

    assert first.chunks_written == second.chunks_written
    assert chunk_count == first.chunks_written
    assert document_count == first.documents_processed
    assert second.chunks_removed >= 0


def test_chunking_preserves_paragraphs() -> None:
    document = sample_document().model_copy(
        update={
            "content": (
                "Paragraph one about metro cards.\n\n"
                "Paragraph two about airport trains."
            ),
        }
    )
    chunks = chunk_document(document, target_tokens=8)
    assert len(chunks) >= 2
    assert all(chunk.document_id == document.id for chunk in chunks)


async def test_version_handling_replaces_chunks_for_same_document_version(
    db_session: AsyncSession,
    fake_embedding_provider: FakeEmbeddingProvider,
) -> None:
    pipeline = RagIngestionPipeline(
        session=db_session,
        embedding_provider=fake_embedding_provider,
    )
    document = sample_document(document_id="version-test-doc", destination="Dubai")
    await pipeline._ingest_document(document, "v-test")
    first_count = await db_session.scalar(
        select(func.count())
        .select_from(RagChunk)
        .where(RagChunk.document_id == "version-test-doc")
    )

    updated = document.model_copy(
        update={"content": document.content + " Updated guidance."}
    )
    await pipeline._ingest_document(updated, "v-test")
    second_count = await db_session.scalar(
        select(func.count())
        .select_from(RagChunk)
        .where(RagChunk.document_id == "version-test-doc")
    )
    await db_session.commit()

    assert first_count == second_count
    assert first_count is not None and first_count > 0
