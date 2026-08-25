"""Deterministic fake embedding provider for offline tests."""

from __future__ import annotations

import hashlib
import math

from app.rag.embeddings.base import EmbeddingProvider


class FakeEmbeddingProvider:
    """Hash-based deterministic embeddings with correct dimensionality."""

    def __init__(
        self, dimensions: int = 1536, model_name: str = "fake-embedding-v1"
    ) -> None:
        self._dimensions = dimensions
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(text) for text in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._vectorize(query)

    def _vectorize(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self._dimensions:
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) >= self._dimensions:
                    break
            digest = hashlib.sha256(digest).digest()
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return values
        return [value / norm for value in values]


def assert_embedding_provider(provider: EmbeddingProvider) -> EmbeddingProvider:
    return provider
