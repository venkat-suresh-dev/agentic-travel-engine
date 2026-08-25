"""Gemini embedding provider implementation."""

from __future__ import annotations

import httpx

from app.rag.embeddings.base import EmbeddingProviderError

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_EMBEDDING_DIMENSIONS = 1536


class GeminiEmbeddingProvider:
    """Live Gemini embeddings for ingestion and retrieval."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = GEMINI_EMBEDDING_MODEL,
        dimensions: int = GEMINI_EMBEDDING_DIMENSIONS,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required for embedding provider")
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
        embeddings: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            for text in texts:
                vector = await self._embed_single(client, text)
                embeddings.append(vector)
        self._validate_vectors(embeddings)
        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        vectors = await self.embed_texts([query])
        return vectors[0]

    async def _embed_single(self, client: httpx.AsyncClient, text: str) -> list[float]:
        model_path = self._model_name
        if not model_path.startswith("models/"):
            model_path = f"models/{model_path}"
        url = f"{self._base_url}/{model_path}:embedContent"
        payload = {
            "model": model_path,
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": self._dimensions,
        }
        response = await client.post(
            url,
            params={"key": self._api_key},
            json=payload,
        )
        if response.status_code >= 400:
            raise EmbeddingProviderError(
                f"Gemini embedding request failed with status {response.status_code}"
            )
        data = response.json()
        embedding = data.get("embedding", {}).get("values")
        if not isinstance(embedding, list):
            raise EmbeddingProviderError("Gemini embedding response missing values")
        return [float(value) for value in embedding]

    def _validate_vectors(self, embeddings: list[list[float]]) -> None:
        for vector in embeddings:
            if len(vector) != self._dimensions:
                raise EmbeddingProviderError(
                    "Expected embedding dimension "
                    f"{self._dimensions}, got {len(vector)}"
                )
