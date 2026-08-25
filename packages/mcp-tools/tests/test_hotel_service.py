"""Hotel MCP tool tests."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from mcp_tools.hotels.cache import HotelCache
from mcp_tools.hotels.exceptions import HotelProviderError, HotelProviderTimeoutError
from mcp_tools.hotels.mcp_server import create_hotels_mcp_server
from mcp_tools.hotels.providers.normalize import parse_amadeus_hotel_offers
from mcp_tools.hotels.schemas import HotelDataStatus, HotelSearchRequest
from mcp_tools.hotels.service import HotelService
from tests.fakes import FakeCityCodeResolver, FakeHotelProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def single_room_request() -> HotelSearchRequest:
    return HotelSearchRequest(
        location="Dubai",
        city_code="DXB",
        check_in=date(2026, 12, 1),
        check_out=date(2026, 12, 6),
        travelers=2,
        rooms=1,
        currency="AED",
    )


@pytest.fixture
def multi_room_request() -> HotelSearchRequest:
    return HotelSearchRequest(
        location="Dubai",
        city_code="DXB",
        check_in=date(2026, 12, 1),
        check_out=date(2026, 12, 6),
        travelers=4,
        rooms=2,
        currency="AED",
    )


def test_single_room_request_validation() -> None:
    request = HotelSearchRequest(
        location="Dubai",
        city_code="DXB",
        check_in=date(2026, 12, 1),
        check_out=date(2026, 12, 6),
        travelers=2,
        rooms=1,
        currency="AED",
    )
    assert request.rooms == 1


def test_multi_room_request_validation() -> None:
    request = HotelSearchRequest(
        location="Dubai",
        city_code="DXB",
        check_in=date(2026, 12, 1),
        check_out=date(2026, 12, 6),
        travelers=4,
        rooms=2,
        currency="AED",
    )
    assert request.rooms == 2


def test_invalid_date_range_rejected() -> None:
    with pytest.raises(ValueError):
        HotelSearchRequest(
            location="Dubai",
            city_code="DXB",
            check_in=date(2026, 12, 6),
            check_out=date(2026, 12, 1),
            travelers=2,
            rooms=1,
            currency="AED",
        )


def test_invalid_traveler_count_rejected() -> None:
    with pytest.raises(ValueError):
        HotelSearchRequest(
            location="Dubai",
            city_code="DXB",
            check_in=date(2026, 12, 1),
            check_out=date(2026, 12, 6),
            travelers=0,
            rooms=1,
            currency="AED",
        )


def test_invalid_room_count_rejected() -> None:
    with pytest.raises(ValueError):
        HotelSearchRequest(
            location="Dubai",
            city_code="DXB",
            check_in=date(2026, 12, 1),
            check_out=date(2026, 12, 6),
            travelers=2,
            rooms=0,
            currency="AED",
        )


def test_invalid_currency_rejected() -> None:
    with pytest.raises(ValueError):
        HotelSearchRequest(
            location="Dubai",
            city_code="DXB",
            check_in=date(2026, 12, 1),
            check_out=date(2026, 12, 6),
            travelers=2,
            rooms=1,
            currency="AB",
        )


def test_invalid_occupancy_rejected() -> None:
    with pytest.raises(ValueError):
        HotelSearchRequest(
            location="Dubai",
            city_code="DXB",
            check_in=date(2026, 12, 1),
            check_out=date(2026, 12, 6),
            travelers=1,
            rooms=2,
            currency="AED",
        )


def test_live_hotel_response_has_provenance(
    single_room_request: HotelSearchRequest,
) -> None:
    service = HotelService(
        hotel_provider=FakeHotelProvider(),
        cache=HotelCache(),
    )

    result, metadata = service.search_hotels(single_room_request)

    assert result.data_status is HotelDataStatus.LIVE
    assert result.source == "amadeus"
    assert result.hotels
    assert result.hotels[0].total_price is not None
    assert result.hotels[0].total_price.amount == Decimal("2250.00")
    assert result.hotels[0].total_price.currency == "AED"
    assert result.hotels[0].is_search_result_only is True
    assert metadata.tool_name == "search_hotels"
    assert metadata.cache_status == "miss"


def test_amadeus_fixture_normalization(
    single_room_request: HotelSearchRequest,
) -> None:
    payload = json.loads((FIXTURES_DIR / "amadeus_hotel_offers.json").read_text())
    hotels = parse_amadeus_hotel_offers(
        payload,
        request=single_room_request,
        location_name="Dubai",
    )

    assert len(hotels) == 2
    first = hotels[0]
    assert first.hotel_id == "HLDXB123"
    assert first.name == "Sample Dubai Marina Hotel"
    assert first.address == "Marina Walk, Dubai, AE"
    assert first.latitude == 25.0805
    assert len(first.room_options) == 2
    assert first.room_options[0].room_type == "Deluxe Room"
    assert first.room_options[0].nightly_price is not None
    assert first.room_options[0].nightly_price.amount == Decimal("450.00")
    assert first.room_options[0].total_price.amount == Decimal("2250.00")
    assert first.nightly_price is not None
    assert first.total_price is not None
    assert first.total_price.amount == Decimal("1600.00")

    second = hotels[1]
    assert second.room_options[0].nightly_price is None
    assert second.room_options[0].total_price.amount == Decimal("1900.00")


def test_malformed_provider_response_is_unavailable(
    single_room_request: HotelSearchRequest,
) -> None:
    service = HotelService(
        hotel_provider=FakeHotelProvider(malformed=True),
        cache=HotelCache(),
    )

    result, _metadata = service.search_hotels(single_room_request)

    assert result.data_status is HotelDataStatus.UNAVAILABLE


def test_cache_hit_returns_cached_status(
    single_room_request: HotelSearchRequest,
) -> None:
    cache = HotelCache(ttl_seconds=120)
    service = HotelService(
        hotel_provider=FakeHotelProvider(),
        cache=cache,
    )
    service.search_hotels(single_room_request)

    failing_service = HotelService(
        hotel_provider=FakeHotelProvider(should_fail=True),
        cache=cache,
    )
    result, metadata = failing_service.search_hotels(single_room_request)

    assert result.data_status is HotelDataStatus.CACHED
    assert metadata.cache_status == "hit"


def test_provider_failure_without_cache_is_unavailable(
    single_room_request: HotelSearchRequest,
) -> None:
    service = HotelService(
        hotel_provider=FakeHotelProvider(should_fail=True),
        cache=HotelCache(),
    )

    result, _metadata = service.search_hotels(single_room_request)

    assert result.data_status is HotelDataStatus.UNAVAILABLE
    assert result.hotels == []


def test_provider_retries_once_before_failure(
    single_room_request: HotelSearchRequest,
) -> None:
    attempts = {"count": 0}

    class FlakyHotelProvider(FakeHotelProvider):
        def search_hotels(self, request):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise HotelProviderError("temporary failure")
            return super().search_hotels(request)

    service = HotelService(
        hotel_provider=FlakyHotelProvider(),
        cache=HotelCache(),
    )

    result, _metadata = service.search_hotels(single_room_request)

    assert attempts["count"] == 2
    assert result.data_status is HotelDataStatus.LIVE


def test_provider_timeout_retries_then_unavailable(
    single_room_request: HotelSearchRequest,
) -> None:
    attempts = {"count": 0}

    class TimeoutHotelProvider(FakeHotelProvider):
        def search_hotels(self, request):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            raise HotelProviderTimeoutError("simulated timeout")

    service = HotelService(
        hotel_provider=TimeoutHotelProvider(),
        cache=HotelCache(),
    )

    result, _metadata = service.search_hotels(single_room_request)

    assert attempts["count"] == 2
    assert result.data_status is HotelDataStatus.UNAVAILABLE


def test_cache_expiry_allows_new_live_fetch(
    single_room_request: HotelSearchRequest,
) -> None:
    cache = HotelCache(ttl_seconds=1)
    service = HotelService(
        hotel_provider=FakeHotelProvider(),
        cache=cache,
    )
    first, _ = service.search_hotels(single_room_request)

    key = HotelCache.cache_key(single_room_request)
    entry = cache.get(key)
    assert entry is not None
    cache._entries[key] = type(entry)(
        result=entry.result,
        stored_at=datetime.now(UTC) - timedelta(seconds=2),
    )

    second, metadata = service.search_hotels(single_room_request)

    assert second.data_status is HotelDataStatus.LIVE
    assert second.retrieved_at >= first.retrieved_at
    assert metadata.cache_status == "miss"


def test_normalized_cache_key(single_room_request: HotelSearchRequest) -> None:
    key = HotelCache.cache_key(single_room_request)
    assert key == "Dubai|DXB|2026-12-01|2026-12-06|2|1|AED"


def test_fake_city_resolver() -> None:
    resolver = FakeCityCodeResolver()
    assert resolver.resolve("Dubai") == "DXB"
    assert resolver.resolve("DXB") == "DXB"


@pytest.mark.asyncio
async def test_mcp_tool_contract(single_room_request: HotelSearchRequest) -> None:
    from mcp import Client

    service = HotelService(
        hotel_provider=FakeHotelProvider(),
        cache=HotelCache(),
    )
    server = create_hotels_mcp_server(service)

    async with Client(server) as client:
        tool_result = await client.call_tool(
            "search_hotels",
            {
                "location": single_room_request.location,
                "city_code": single_room_request.city_code,
                "check_in": single_room_request.check_in.isoformat(),
                "check_out": single_room_request.check_out.isoformat(),
                "travelers": single_room_request.travelers,
                "rooms": single_room_request.rooms,
                "currency": single_room_request.currency,
            },
        )

    payload = tool_result.structured_content
    assert payload["data_status"] == HotelDataStatus.LIVE.value
    assert payload["hotels"]
