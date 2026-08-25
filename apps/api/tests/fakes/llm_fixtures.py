"""Shared LLM fake fixtures."""

from __future__ import annotations

import pytest

from tests.fakes.llm import FakeLLMAdapter


@pytest.fixture
def fake_adapter() -> FakeLLMAdapter:
    return FakeLLMAdapter.from_stub()
