"""Groq OpenAI-compatible implementation of the LLM adapter."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.llm.exceptions import LLMProviderError, LLMStructuredOutputError
from app.llm.types import LLMCallMetadata, StructuredLLMResult

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GroqLLMAdapter:
    """Structured extraction through Groq's OpenAI-compatible chat API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            msg = "Groq API key is not configured"
            raise LLMProviderError(msg)
        self._settings = settings
        self._base_url = settings.groq_base_url.rstrip("/")

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> StructuredLLMResult[T]:
        started = time.perf_counter()
        model = self._settings.groq_model
        status = "success"

        payload = {
            "model": model,
            "max_tokens": self._settings.llm_max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                },
            },
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._settings.groq_api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            status = "provider_error"
            latency_ms = (time.perf_counter() - started) * 1000
            logger.warning(
                "groq structured extraction failed",
                extra={
                    "provider": "groq",
                    "model": model,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "user_prompt_length": len(user_prompt),
                },
            )
            raise LLMProviderError(str(exc)) from exc

        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            status = "provider_error"
            logger.warning(
                "groq structured extraction rejected",
                extra={
                    "provider": "groq",
                    "model": model,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "http_status": response.status_code,
                    "user_prompt_length": len(user_prompt),
                },
            )
            raise LLMProviderError(
                f"Groq request failed with status {response.status_code}"
            )

        try:
            body = response.json()
            content = _extract_message_content(body)
            parsed_payload = json.loads(content)
        except (ValueError, KeyError, TypeError) as exc:
            status = "missing_parsed_output"
            logger.warning(
                "groq structured extraction returned invalid payload",
                extra={
                    "provider": "groq",
                    "model": model,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "user_prompt_length": len(user_prompt),
                },
            )
            raise LLMStructuredOutputError(
                "Groq response did not contain parseable structured output"
            ) from exc

        try:
            validated = response_model.model_validate(parsed_payload)
        except ValidationError as exc:
            status = "schema_validation_error"
            logger.warning(
                "groq structured extraction failed schema validation",
                extra={
                    "provider": "groq",
                    "model": model,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "user_prompt_length": len(user_prompt),
                },
            )
            raise LLMStructuredOutputError(str(exc)) from exc

        usage = body.get("usage") if isinstance(body, dict) else None
        input_tokens = _usage_value(usage, "prompt_tokens")
        output_tokens = _usage_value(usage, "completion_tokens")

        logger.info(
            "groq structured extraction succeeded",
            extra={
                "provider": "groq",
                "model": model,
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "user_prompt_length": len(user_prompt),
            },
        )

        return StructuredLLMResult(
            data=validated,
            metadata=LLMCallMetadata(
                provider="groq",
                model=model,
                status=status,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        )


def _extract_message_content(body: dict[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        msg = "Groq response missing choices"
        raise KeyError(msg)
    message = choices[0].get("message")
    if not isinstance(message, dict):
        msg = "Groq response missing message"
        raise KeyError(msg)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        msg = "Groq response missing content"
        raise KeyError(msg)
    return content


def _usage_value(usage: object, field: str) -> int | None:
    if not isinstance(usage, dict):
        return None
    value = usage.get(field)
    return int(value) if isinstance(value, int) else None
