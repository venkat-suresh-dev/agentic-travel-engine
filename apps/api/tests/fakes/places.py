"""Fake places tool wiring for API tests."""

from __future__ import annotations

import pytest
from app.tools.attractions import AttractionTool
from app.tools.restaurants import RestaurantTool
from mcp_tools.places.cache import PlacesCache
from mcp_tools.places.service import PlacesService

from tests.fakes.places_providers import FakePlacesProvider


@pytest.fixture
def fake_places_service() -> PlacesService:
    return PlacesService(
        places_provider=FakePlacesProvider(),
        cache=PlacesCache(),
    )


@pytest.fixture
def fake_restaurant_tool(fake_places_service: PlacesService) -> RestaurantTool:
    return RestaurantTool(fake_places_service)


@pytest.fixture
def fake_attraction_tool(fake_places_service: PlacesService) -> AttractionTool:
    return AttractionTool(fake_places_service)
