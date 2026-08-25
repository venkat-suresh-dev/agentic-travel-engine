"""Anthropic Claude implementation of the LLM adapter."""

from __future__ import annotations

import logging
import time
from typing import TypeVar

import anthropic
from anthropic import Anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.llm.exceptions import LLMProviderError, LLMStructuredOutputError
from app.llm.types import LLMCallMetadata, StructuredLLMResult

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AnthropicLLMAdapter:
    """Structured extraction through Anthropic's official SDK."""

    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            msg = "Anthropic API key is not configured"
            raise LLMProviderError(msg)
        self._settings = settings
        self._client = Anthropic(api_key=settings.anthropic_api_key)

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> StructuredLLMResult[T]:
        started = time.perf_counter()
        model = self._settings.anthropic_model
        status = "success"

        try:
            response = self._client.messages.parse(
                model=model,
                max_tokens=self._settings.llm_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                output_format=response_model,
            )
        except anthropic.APIError as exc:
            status = "provider_error"
            latency_ms = (time.perf_counter() - started) * 1000
            logger.warning(
                "anthropic structured extraction failed",
                extra={
                    "provider": "anthropic",
                    "model": model,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "user_prompt_length": len(user_prompt),
                },
            )
            raise LLMProviderError(str(exc)) from exc

        latency_ms = (time.perf_counter() - started) * 1000
        parsed_output = response.parsed_output
        if parsed_output is None:
            status = "missing_parsed_output"
            logger.warning(
                "anthropic structured extraction returned no parsed output",
                extra={
                    "provider": "anthropic",
                    "model": model,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "user_prompt_length": len(user_prompt),
                },
            )
            raise LLMStructuredOutputError(
                "Anthropic response did not contain parsed structured output"
            )

        try:
            validated = response_model.model_validate(parsed_output.model_dump())
        except ValidationError as exc:
            status = "schema_validation_error"
            logger.warning(
                "anthropic structured extraction failed schema validation",
                extra={
                    "provider": "anthropic",
                    "model": model,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "user_prompt_length": len(user_prompt),
                },
            )
            raise LLMStructuredOutputError(str(exc)) from exc

        usage = response.usage
        logger.info(
            "anthropic structured extraction succeeded",
            extra={
                "provider": "anthropic",
                "model": model,
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "input_tokens": usage.input_tokens if usage else None,
                "output_tokens": usage.output_tokens if usage else None,
                "user_prompt_length": len(user_prompt),
            },
        )

        return StructuredLLMResult(
            data=validated,
            metadata=LLMCallMetadata(
                provider="anthropic",
                model=model,
                status=status,
                latency_ms=latency_ms,
                input_tokens=usage.input_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
            ),
        )
