"""Shared LLM adapter types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMCallMetadata:
    """Basic observability metadata for a single LLM call."""

    provider: str
    model: str
    status: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class StructuredLLMResult[T]:
    """Validated structured output from an LLM adapter."""

    data: T
    metadata: LLMCallMetadata
