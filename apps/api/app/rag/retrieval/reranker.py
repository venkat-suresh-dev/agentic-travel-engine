"""Optional reranker abstraction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.rag.schemas import RetrievedChunk


@runtime_checkable
class Reranker(Protocol):
    async def rerank(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]: ...


class NoOpReranker:
    """Default reranker that preserves hybrid ordering."""

    async def rerank(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        _ = query
        return chunks
