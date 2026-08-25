"""PostgreSQL vector similarity retrieval."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.rag import RagChunk
from app.rag.retrieval.merger import topic_values
from app.rag.schemas import RagTopic, RetrievalMethod, RetrievedChunk


class VectorRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        *,
        query_embedding: list[float],
        destination: str,
        top_k: int,
        topics: list[RagTopic] | None = None,
    ) -> list[RetrievedChunk]:
        stmt: Select[tuple[RagChunk, float]] = (
            select(
                RagChunk,
                (1 - RagChunk.embedding.cosine_distance(query_embedding)).label(
                    "score"
                ),
            )
            .where(RagChunk.destination.ilike(destination.strip()))
            .order_by(RagChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        topic_filter = topic_values(topics)
        if topic_filter is not None:
            stmt = stmt.where(RagChunk.topic.in_(topic_filter))

        rows = (await self._session.execute(stmt)).all()
        return [self._to_chunk(row[0], float(row[1])) for row in rows]

    def _to_chunk(self, row: RagChunk, score: float) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=row.chunk_id,
            content=row.content,
            score=round(score, 6),
            retrieval_method=RetrievalMethod.VECTOR,
            destination=row.destination,
            topic=RagTopic(row.topic),
            source_url=row.source_url,
            source_name=row.source_name,
            document_version=row.document_version,
            last_verified=_as_date(row.last_verified),
            document_id=row.document_id,
            chunk_index=row.chunk_index,
        )


def _as_date(value: date) -> date:
    return value
