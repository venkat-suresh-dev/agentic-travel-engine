"""Application service boundary for destination knowledge retrieval."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings.base import EmbeddingProvider
from app.rag.formatting.context import format_retrieved_context
from app.rag.retrieval.hybrid import HybridRetriever
from app.rag.retrieval.reranker import Reranker
from app.rag.schemas import RetrievalRequest, RetrievedContext


class RAGRetriever:
    """High-level retrieval service for future graph/LLM consumers."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        reranker: Reranker | None = None,
    ) -> None:
        self._hybrid = HybridRetriever(
            session=session,
            embedding_provider=embedding_provider,
            reranker=reranker,
        )

    async def retrieve(self, request: RetrievalRequest) -> RetrievedContext:
        return await self._hybrid.retrieve(request)

    def format_context(self, context: RetrievedContext) -> str:
        return format_retrieved_context(context)
