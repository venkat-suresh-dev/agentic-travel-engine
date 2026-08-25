"""Deterministic corpus ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.rag import RagChunk, RagDocument
from app.rag.chunking import chunk_document
from app.rag.corpus.loader import load_corpus_documents
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.ingestion.cleaner import clean_text
from app.rag.ingestion.validator import validate_document
from app.rag.schemas import CorpusChunk, CorpusDocument, IngestionReport


class RagIngestionPipeline:
    """ingest -> clean -> validate -> chunk -> embed -> persist."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        target_chunk_tokens: int = 400,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider
        self._target_chunk_tokens = target_chunk_tokens

    async def ingest_corpus(self, corpus_path: Path | None = None) -> IngestionReport:
        corpus_version, documents = load_corpus_documents(corpus_path)
        chunks_written = 0
        chunks_removed = 0

        for document in documents:
            removed, written = await self._ingest_document(document, corpus_version)
            chunks_removed += removed
            chunks_written += written

        await self._session.commit()
        return IngestionReport(
            documents_processed=len(documents),
            chunks_written=chunks_written,
            chunks_removed=chunks_removed,
            corpus_version=corpus_version,
        )

    async def _ingest_document(
        self,
        raw_document: CorpusDocument,
        corpus_version: str,
    ) -> tuple[int, int]:
        cleaned = raw_document.model_copy(
            update={"content": clean_text(raw_document.content)}
        )
        document = validate_document(cleaned)
        chunks = chunk_document(
            document,
            target_tokens=self._target_chunk_tokens,
        )
        embeddings = await self._embedding_provider.embed_texts(
            [chunk.search_text for chunk in chunks]
        )

        rag_document = await self._upsert_document(document, corpus_version)
        removed = await self._replace_chunks(rag_document, chunks, embeddings)
        return removed, len(chunks)

    async def _upsert_document(
        self,
        document: CorpusDocument,
        corpus_version: str,
    ) -> RagDocument:
        result = await self._session.execute(
            select(RagDocument).where(
                RagDocument.document_id == document.id,
                RagDocument.document_version == document.version,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            existing = RagDocument(
                document_id=document.id,
                destination=document.destination,
                country=document.country,
                topic=document.topic.value,
                title=document.title,
                source_url=document.source_url,
                source_name=document.source_name,
                last_verified=document.last_verified,
                document_version=document.version,
                corpus_version=corpus_version,
            )
            self._session.add(existing)
            await self._session.flush()
            return existing

        existing.destination = document.destination
        existing.country = document.country
        existing.topic = document.topic.value
        existing.title = document.title
        existing.source_url = document.source_url
        existing.source_name = document.source_name
        existing.last_verified = document.last_verified
        existing.corpus_version = corpus_version
        await self._session.flush()
        return existing

    async def _replace_chunks(
        self,
        rag_document: RagDocument,
        chunks: list[CorpusChunk],
        embeddings: list[list[float]],
    ) -> int:
        delete_result = await self._session.execute(
            delete(RagChunk).where(RagChunk.rag_document_id == rag_document.id)
        )
        removed = int(getattr(delete_result, "rowcount", 0) or 0)

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._session.add(
                RagChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    rag_document_id=rag_document.id,
                    destination=chunk.destination,
                    topic=chunk.topic.value,
                    content=chunk.content,
                    source_url=chunk.source_url,
                    source_name=chunk.source_name,
                    document_version=chunk.document_version,
                    last_verified=chunk.last_verified,
                    chunk_index=chunk.chunk_index,
                    search_text=chunk.search_text,
                    embedding=embedding,
                )
            )
        await self._session.flush()
        return removed
