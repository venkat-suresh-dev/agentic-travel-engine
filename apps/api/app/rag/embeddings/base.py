"""Embedding provider abstraction for RAG ingestion and retrieval."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider fails."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Provider-independent embedding contract."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed one or more texts, returning one vector per input text."""

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single retrieval query."""
