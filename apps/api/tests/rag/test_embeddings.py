"""Embedding provider tests."""

from __future__ import annotations

import pytest
from app.rag.embeddings.base import EmbeddingProvider, EmbeddingProviderError
from app.rag.embeddings.fake import FakeEmbeddingProvider, assert_embedding_provider
from app.rag.embeddings.openai import OpenAIEmbeddingProvider


async def test_fake_embedding_provider_is_deterministic() -> None:
    provider = FakeEmbeddingProvider(dimensions=1536)
    first = await provider.embed_query("Dubai metro")
    second = await provider.embed_query("Dubai metro")
    different = await provider.embed_query("Tokyo metro")

    assert len(first) == 1536
    assert first == second
    assert first != different


async def test_fake_embedding_provider_dimensionality_validation() -> None:
    provider = FakeEmbeddingProvider(dimensions=8)
    vectors = await provider.embed_texts(["one", "two"])
    assert len(vectors) == 2
    assert all(len(vector) == 8 for vector in vectors)


def test_embedding_provider_protocol() -> None:
    provider = assert_embedding_provider(FakeEmbeddingProvider())
    assert isinstance(provider, EmbeddingProvider)


async def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValueError):
        OpenAIEmbeddingProvider(api_key="")


async def test_openai_provider_validates_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAIEmbeddingProvider(api_key="test-key", dimensions=4)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {"data": [{"embedding": [0.1, 0.2]}]}

    class FakeClient:
        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        "app.rag.embeddings.openai.httpx.AsyncClient", lambda **kwargs: FakeClient()
    )

    with pytest.raises(EmbeddingProviderError):
        await provider.embed_texts(["hello"])
