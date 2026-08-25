"""Provider-agnostic LLM adapter interface."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.llm.types import StructuredLLMResult

T = TypeVar("T", bound=BaseModel)


class LLMAdapter(Protocol):
    """Extract structured data from natural-language input."""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> StructuredLLMResult[T]:
        """Return provider output validated against ``response_model``."""
