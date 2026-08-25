"""Fake hotel tool wiring for API tests."""

from __future__ import annotations

import pytest
from app.tools.hotels import HotelTool
from mcp_tools.hotels.cache import HotelCache
from mcp_tools.hotels.service import HotelService

from tests.fakes.hotels_providers import FakeCityCodeResolver, FakeHotelProvider


@pytest.fixture
def fake_city_resolver() -> FakeCityCodeResolver:
    return FakeCityCodeResolver()


@pytest.fixture
def fake_hotel_service() -> HotelService:
    return HotelService(
        hotel_provider=FakeHotelProvider(),
        cache=HotelCache(),
    )


@pytest.fixture
def fake_hotel_tool(fake_hotel_service: HotelService) -> HotelTool:
    return HotelTool(fake_hotel_service)
