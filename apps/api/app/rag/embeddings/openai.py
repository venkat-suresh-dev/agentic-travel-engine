"""OpenAI embedding provider implementation."""

from __future__ import annotations

import httpx

from app.rag.embeddings.base import EmbeddingProviderError

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIMENSIONS = 1536


class OpenAIEmbeddingProvider:
    """Live OpenAI embeddings for ingestion and retrieval."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = OPENAI_EMBEDDING_MODEL,
        dimensions: int = OPENAI_EMBEDDING_DIMENSIONS,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for embedding provider")
        self._api_key = api_key
        self._model_name = model_name
        self._dimensions = dimensions
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self._model_name,
            "input": texts,
            "dimensions": self._dimensions,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
        if response.status_code >= 400:
            raise EmbeddingProviderError(
                f"OpenAI embedding request failed with status {response.status_code}"
            )
        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        self._validate_vectors(embeddings)
        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        vectors = await self.embed_texts([query])
        return vectors[0]

    def _validate_vectors(self, embeddings: list[list[float]]) -> None:
        for vector in embeddings:
            if len(vector) != self._dimensions:
                raise EmbeddingProviderError(
                    "Expected embedding dimension "
                    f"{self._dimensions}, got {len(vector)}"
                )
