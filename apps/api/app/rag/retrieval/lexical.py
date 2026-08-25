"""PostgreSQL lexical/full-text retrieval."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.retrieval.merger import topic_values
from app.rag.schemas import RagTopic, RetrievalMethod, RetrievedChunk


class LexicalRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        *,
        query: str,
        destination: str,
        top_k: int,
        topics: list[RagTopic] | None = None,
    ) -> list[RetrievedChunk]:
        topic_filter = topic_values(topics)
        sql = """
            SELECT
                chunk_id,
                document_id,
                destination,
                topic,
                content,
                source_url,
                source_name,
                document_version,
                last_verified,
                chunk_index,
                ts_rank(
                    to_tsvector('english', search_text),
                    plainto_tsquery('english', :query)
                ) AS score
            FROM rag_chunks
            WHERE destination ILIKE :destination
              AND to_tsvector('english', search_text)
                  @@ plainto_tsquery('english', :query)
        """
        params: dict[str, object] = {
            "query": query,
            "destination": destination.strip(),
            "top_k": top_k,
        }
        if topic_filter is not None:
            sql += " AND topic = ANY(:topics)"
            params["topics"] = topic_filter
        sql += " ORDER BY score DESC, chunk_index ASC LIMIT :top_k"

        rows = (await self._session.execute(text(sql), params)).mappings().all()
        return [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                content=row["content"],
                score=round(float(row["score"]), 6),
                retrieval_method=RetrievalMethod.LEXICAL,
                destination=row["destination"],
                topic=RagTopic(row["topic"]),
                source_url=row["source_url"],
                source_name=row["source_name"],
                document_version=row["document_version"],
                last_verified=_as_date(row["last_verified"]),
                document_id=row["document_id"],
                chunk_index=row["chunk_index"],
            )
            for row in rows
        ]


def _as_date(value: date) -> date:
    return value
