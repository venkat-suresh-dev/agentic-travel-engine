"""LLM provider and structured-output errors."""


class LLMProviderError(Exception):
    """Raised when the upstream LLM provider request fails."""


class LLMStructuredOutputError(Exception):
    """Raised when provider output cannot be validated against the expected schema."""
