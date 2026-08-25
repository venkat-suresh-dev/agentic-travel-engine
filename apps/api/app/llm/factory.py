"""LLM adapter construction."""

from __future__ import annotations

from app.core.config import Settings, settings
from app.llm.anthropic import AnthropicLLMAdapter
from app.llm.base import LLMAdapter
from app.llm.groq import GroqLLMAdapter


def build_llm_adapter(app_settings: Settings | None = None) -> LLMAdapter:
    """Create the configured LLM adapter for the application."""
    resolved_settings = app_settings or settings
    provider = resolved_settings.llm_provider.lower()

    if provider == "anthropic":
        return AnthropicLLMAdapter(resolved_settings)
    if provider == "groq":
        return GroqLLMAdapter(resolved_settings)

    msg = f"Unsupported LLM provider: {resolved_settings.llm_provider}"
    raise ValueError(msg)
