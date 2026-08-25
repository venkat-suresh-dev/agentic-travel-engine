"""Hybrid destination knowledge retrieval."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings.base import EmbeddingProvider
from app.rag.retrieval.lexical import LexicalRetriever
from app.rag.retrieval.merger import merge_ranked_results
from app.rag.retrieval.reranker import NoOpReranker, Reranker
from app.rag.retrieval.vector import VectorRetriever
from app.rag.schemas import RetrievalRequest, RetrievedContext


class HybridRetriever:
    """Vector + lexical retrieval with deterministic merge/rank."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        reranker: Reranker | None = None,
        candidate_multiplier: int = 3,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider
        self._vector = VectorRetriever(session)
        self._lexical = LexicalRetriever(session)
        self._reranker = reranker or NoOpReranker()
        self._candidate_multiplier = candidate_multiplier

    async def retrieve(self, request: RetrievalRequest) -> RetrievedContext:
        candidate_k = max(request.top_k * self._candidate_multiplier, request.top_k)
        query_embedding = await self._embedding_provider.embed_query(request.query)

        vector_results = await self._vector.retrieve(
            query_embedding=query_embedding,
            destination=request.destination,
            top_k=candidate_k,
            topics=request.topics,
        )
        lexical_results = await self._lexical.retrieve(
            query=request.query,
            destination=request.destination,
            top_k=candidate_k,
            topics=request.topics,
        )
        merged = merge_ranked_results(
            vector_results=vector_results,
            lexical_results=lexical_results,
            top_k=request.top_k,
        )
        reranked = await self._reranker.rerank(query=request.query, chunks=merged)
        return RetrievedContext(
            query=request.query,
            destination=request.destination,
            chunks=reranked,
            retrieved_at=datetime.now(UTC),
            is_reference_data_only=True,
        )
