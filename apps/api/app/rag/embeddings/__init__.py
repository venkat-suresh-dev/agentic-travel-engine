"""Embedding provider factory."""

from __future__ import annotations

from app.core.config import Settings
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.embeddings.fake import FakeEmbeddingProvider
from app.rag.embeddings.openai import (
    OPENAI_EMBEDDING_DIMENSIONS,
    OPENAI_EMBEDDING_MODEL,
    OpenAIEmbeddingProvider,
)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider_name = settings.rag_embedding_provider.lower()
    if provider_name == "fake":
        return FakeEmbeddingProvider(
            dimensions=settings.rag_embedding_dimensions,
            model_name=settings.rag_embedding_model,
        )
    if provider_name == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model_name=settings.rag_embedding_model,
            dimensions=settings.rag_embedding_dimensions,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.rag_embedding_timeout_seconds,
        )
    raise ValueError(f"Unsupported RAG embedding provider: {provider_name}")


__all__ = [
    "OPENAI_EMBEDDING_DIMENSIONS",
    "OPENAI_EMBEDDING_MODEL",
    "build_embedding_provider",
]
