"""RAG retriever construction."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, settings
from app.rag.embeddings import build_embedding_provider
from app.rag.formatting.context import format_retrieved_context
from app.rag.schemas import RetrievalRequest, RetrievedContext
from app.rag.service import RAGRetriever


class SessionScopedRAGRetriever:
    """RAG retriever that opens a database session per retrieval call."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: object,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_provider = embedding_provider

    async def retrieve(self, request: RetrievalRequest) -> RetrievedContext:
        async with self._session_factory() as session:
            retriever = RAGRetriever(
                session=session,
                embedding_provider=self._embedding_provider,  # type: ignore[arg-type]
            )
            return await retriever.retrieve(request)

    def format_context(self, context: RetrievedContext) -> str:
        return format_retrieved_context(context)


def build_rag_retriever(
    session_factory: async_sessionmaker[AsyncSession],
    config: Settings | None = None,
) -> SessionScopedRAGRetriever | None:
    """Build a session-scoped RAG retriever when embeddings are configured."""
    cfg = config or settings
    if cfg.rag_embedding_provider.lower() == "fake":
        return None
    embedding_provider = build_embedding_provider(cfg)
    return SessionScopedRAGRetriever(
        session_factory=session_factory,
        embedding_provider=embedding_provider,
    )
