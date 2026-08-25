"""Fake distance tool wiring for API tests."""

from __future__ import annotations

import pytest
from app.tools.distance import DistanceTool
from mcp_tools.distance.cache import DistanceCache
from mcp_tools.distance.service import DistanceService

from tests.fakes.distance_providers import FakeDistanceProvider, FakeLocationResolver


@pytest.fixture
def fake_location_resolver() -> FakeLocationResolver:
    return FakeLocationResolver()


@pytest.fixture
def fake_distance_service() -> DistanceService:
    return DistanceService(
        distance_provider=FakeDistanceProvider(),
        cache=DistanceCache(),
    )


@pytest.fixture
def fake_distance_tool(fake_distance_service: DistanceService) -> DistanceTool:
    return DistanceTool(fake_distance_service)
