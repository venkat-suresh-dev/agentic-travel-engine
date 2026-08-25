"""Fake LLM adapter for deterministic tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

from app.domain.trip_request import TripRequest
from app.llm.exceptions import LLMProviderError, LLMStructuredOutputError
from app.llm.types import LLMCallMetadata, StructuredLLMResult
from pydantic import BaseModel, ValidationError

from tests.fakes.extract_stub import extract_from_text

T = TypeVar("T", bound=BaseModel)


class FakeLLMAdapter:
    """Deterministic adapter double for graph and extraction tests."""

    def __init__(
        self,
        extractor: Callable[[str, str, type[BaseModel]], BaseModel] | None = None,
        *,
        provider: str = "fake",
        model: str = "fake-model",
        should_fail: bool = False,
        malformed_payload: dict[str, object] | None = None,
    ) -> None:
        self._extractor = extractor or self._default_extractor
        self._provider = provider
        self._model = model
        self._should_fail = should_fail
        self._malformed_payload = malformed_payload

    @classmethod
    def from_stub(cls) -> FakeLLMAdapter:
        """Create an adapter backed by the deterministic extraction stub."""
        return cls()

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> StructuredLLMResult[T]:
        if self._should_fail:
            raise LLMProviderError("simulated provider failure")

        if self._malformed_payload is not None:
            try:
                data = response_model.model_validate(self._malformed_payload)
            except ValidationError as exc:
                raise LLMStructuredOutputError(str(exc)) from exc
            return StructuredLLMResult(
                data=data,
                metadata=LLMCallMetadata(
                    provider=self._provider,
                    model=self._model,
                    status="success",
                    latency_ms=0.0,
                ),
            )

        data = cast(T, self._extractor(system_prompt, user_prompt, response_model))
        return StructuredLLMResult(
            data=data,
            metadata=LLMCallMetadata(
                provider=self._provider,
                model=self._model,
                status="success",
                latency_ms=0.0,
            ),
        )

    def _default_extractor(
        self,
        _system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        if response_model is not TripRequest:
            msg = f"Fake adapter does not support {response_model.__name__}"
            raise LLMStructuredOutputError(msg)

        if "New user clarification:" in user_prompt:
            clarification = user_prompt.split("New user clarification:", 1)[1].strip()
            return extract_from_text(clarification)  # type: ignore[return-value]

        if (
            "Extract structured trip requirements from this user request:"
            in user_prompt
        ):
            user_text = user_prompt.split(
                "Extract structured trip requirements from this user request:",
                1,
            )[1].strip()
            return extract_from_text(user_text)  # type: ignore[return-value]

        return extract_from_text(user_prompt)  # type: ignore[return-value]
