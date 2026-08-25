"""Shared RAG test fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date
from pathlib import Path

import pytest_asyncio
from app.rag.embeddings.fake import FakeEmbeddingProvider
from app.rag.ingestion.pipeline import RagIngestionPipeline
from app.rag.schemas import CorpusDocument, RagTopic
from app.rag.service import RAGRetriever
from sqlalchemy.ext.asyncio import AsyncSession

TEST_CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "rag"
    / "corpus"
    / "dubai"
    / "corpus.json"
)


@pytest_asyncio.fixture
async def fake_embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider(dimensions=1536)


@pytest_asyncio.fixture
async def ingested_rag_corpus(
    db_session: AsyncSession,
    fake_embedding_provider: FakeEmbeddingProvider,
) -> AsyncGenerator[tuple[AsyncSession, FakeEmbeddingProvider]]:
    pipeline = RagIngestionPipeline(
        session=db_session,
        embedding_provider=fake_embedding_provider,
    )
    await pipeline.ingest_corpus(TEST_CORPUS_PATH)
    yield db_session, fake_embedding_provider


@pytest_asyncio.fixture
async def rag_retriever(
    ingested_rag_corpus: tuple[AsyncSession, FakeEmbeddingProvider],
) -> RAGRetriever:
    session, provider = ingested_rag_corpus
    return RAGRetriever(session=session, embedding_provider=provider)


def sample_document(
    *,
    document_id: str = "tokyo-transport",
    destination: str = "Tokyo",
    version: str = "v1",
) -> CorpusDocument:
    return CorpusDocument(
        id=document_id,
        destination=destination,
        country="Japan",
        topic=RagTopic.TRANSPORT,
        title="Tokyo transport basics",
        source_url="https://example.com/tokyo-transport",
        source_name="Example Transport Guide",
        content="Tokyo has an extensive metro network and rail passes for visitors.",
        last_verified=date(2026, 1, 15),
        version=version,
    )
