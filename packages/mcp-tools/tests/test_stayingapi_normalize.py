"""Tests for StayingAPI hotel normalization."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from mcp_tools.hotels.providers.stayingapi_normalize import parse_stayingapi_properties
from mcp_tools.hotels.schemas import HotelSearchRequest

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_stayingapi_properties() -> None:
    payload = json.loads((FIXTURES / "stayingapi_hotels.json").read_text())
    request = HotelSearchRequest(
        location="Dubai",
        city_code="DXB",
        check_in=date(2026, 9, 1),
        check_out=date(2026, 9, 6),
        travelers=2,
        rooms=1,
        currency="INR",
    )
    hotels = parse_stayingapi_properties(payload, request=request)
    assert len(hotels) == 1
    hotel = hotels[0]
    assert hotel.hotel_id == "stay-123"
    assert hotel.name == "Dubai Marina Hotel"
    assert hotel.nightly_price is not None
    assert hotel.nightly_price.amount == Decimal("8500")
    assert hotel.total_price is not None
    assert hotel.total_price.amount == Decimal("42500")
