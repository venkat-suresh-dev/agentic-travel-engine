"""Flight MCP tool tests."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from mcp_tools.flights.cache import FlightCache
from mcp_tools.flights.exceptions import FlightProviderError, FlightProviderTimeoutError
from mcp_tools.flights.mcp_server import create_flights_mcp_server
from mcp_tools.flights.providers.normalize import parse_amadeus_flight_offers
from mcp_tools.flights.schemas import CabinClass, FlightDataStatus, FlightSearchRequest
from mcp_tools.flights.service import FlightService
from tests.fakes import FakeAirportCodeResolver, FakeFlightProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def one_way_request() -> FlightSearchRequest:
    return FlightSearchRequest(
        origin="BOM",
        destination="DXB",
        departure_date=date(2026, 12, 1),
        travelers=2,
        currency="INR",
    )


@pytest.fixture
def round_trip_request() -> FlightSearchRequest:
    return FlightSearchRequest(
        origin="BOM",
        destination="DXB",
        departure_date=date(2026, 12, 1),
        return_date=date(2026, 12, 6),
        travelers=2,
        currency="INR",
        cabin_class=CabinClass.BUSINESS,
    )


def test_one_way_request_validation() -> None:
    request = FlightSearchRequest(
        origin="BOM",
        destination="DXB",
        departure_date=date(2026, 12, 1),
        travelers=1,
        currency="INR",
    )
    assert request.return_date is None


def test_round_trip_request_validation() -> None:
    request = FlightSearchRequest(
        origin="BOM",
        destination="DXB",
        departure_date=date(2026, 12, 1),
        return_date=date(2026, 12, 6),
        travelers=2,
        currency="INR",
    )
    assert request.return_date == date(2026, 12, 6)


def test_invalid_date_range_rejected() -> None:
    with pytest.raises(ValueError):
        FlightSearchRequest(
            origin="BOM",
            destination="DXB",
            departure_date=date(2026, 12, 10),
            return_date=date(2026, 12, 1),
            travelers=2,
            currency="INR",
        )


def test_invalid_traveler_count_rejected() -> None:
    with pytest.raises(ValueError):
        FlightSearchRequest(
            origin="BOM",
            destination="DXB",
            departure_date=date(2026, 12, 1),
            travelers=0,
            currency="INR",
        )


def test_same_origin_destination_rejected() -> None:
    with pytest.raises(ValueError):
        FlightSearchRequest(
            origin="BOM",
            destination="BOM",
            departure_date=date(2026, 12, 1),
            travelers=1,
            currency="INR",
        )


def test_live_flight_response_has_provenance(
    one_way_request: FlightSearchRequest,
) -> None:
    service = FlightService(
        flight_provider=FakeFlightProvider(),
        cache=FlightCache(),
    )

    result, metadata = service.search_flights(one_way_request)

    assert result.data_status is FlightDataStatus.LIVE
    assert result.source == "amadeus"
    assert result.offers
    assert result.offers[0].price_amount == Decimal("45000")
    assert result.offers[0].price_currency == "INR"
    assert result.offers[0].is_search_result_only is True
    assert metadata.tool_name == "search_flights"
    assert metadata.cache_status == "miss"


def test_amadeus_fixture_normalization(round_trip_request: FlightSearchRequest) -> None:
    payload = json.loads((FIXTURES_DIR / "amadeus_flight_offers.json").read_text())
    offers = parse_amadeus_flight_offers(payload, request=round_trip_request)

    assert len(offers) == 1
    offer = offers[0]
    assert offer.carrier == "EK"
    assert len(offer.itineraries) == 2
    assert offer.itineraries[0].segments[0].flight_number == "EK501"
    assert offer.itineraries[1].segments[0].carrier == "AI"


def test_cache_hit_returns_cached_status(one_way_request: FlightSearchRequest) -> None:
    cache = FlightCache(ttl_seconds=300)
    service = FlightService(
        flight_provider=FakeFlightProvider(),
        cache=cache,
    )
    service.search_flights(one_way_request)

    failing_service = FlightService(
        flight_provider=FakeFlightProvider(should_fail=True),
        cache=cache,
    )
    result, metadata = failing_service.search_flights(one_way_request)

    assert result.data_status is FlightDataStatus.CACHED
    assert metadata.cache_status == "hit"


def test_provider_failure_without_cache_is_unavailable(
    one_way_request: FlightSearchRequest,
) -> None:
    service = FlightService(
        flight_provider=FakeFlightProvider(should_fail=True),
        cache=FlightCache(),
    )

    result, _metadata = service.search_flights(one_way_request)

    assert result.data_status is FlightDataStatus.UNAVAILABLE
    assert result.offers == []


def test_provider_retries_once_before_failure(
    one_way_request: FlightSearchRequest,
) -> None:
    attempts = {"count": 0}

    class FlakyFlightProvider(FakeFlightProvider):
        def search_flights(self, request):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise FlightProviderError("temporary failure")
            return super().search_flights(request)

    service = FlightService(
        flight_provider=FlakyFlightProvider(),
        cache=FlightCache(),
    )

    result, _metadata = service.search_flights(one_way_request)

    assert attempts["count"] == 2
    assert result.data_status is FlightDataStatus.LIVE


def test_provider_timeout_retries_then_unavailable(
    one_way_request: FlightSearchRequest,
) -> None:
    attempts = {"count": 0}

    class TimeoutFlightProvider(FakeFlightProvider):
        def search_flights(self, request):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            raise FlightProviderTimeoutError("simulated timeout")

    service = FlightService(
        flight_provider=TimeoutFlightProvider(),
        cache=FlightCache(),
    )

    result, _metadata = service.search_flights(one_way_request)

    assert attempts["count"] == 2
    assert result.data_status is FlightDataStatus.UNAVAILABLE


def test_malformed_provider_response_is_unavailable(
    one_way_request: FlightSearchRequest,
) -> None:
    service = FlightService(
        flight_provider=FakeFlightProvider(malformed=True),
        cache=FlightCache(),
    )

    result, _metadata = service.search_flights(one_way_request)

    assert result.data_status is FlightDataStatus.UNAVAILABLE


def test_cache_expiry_allows_new_live_fetch(
    one_way_request: FlightSearchRequest,
) -> None:
    cache = FlightCache(ttl_seconds=1)
    service = FlightService(
        flight_provider=FakeFlightProvider(),
        cache=cache,
    )
    first, _ = service.search_flights(one_way_request)

    key = FlightCache.cache_key(one_way_request)
    entry = cache.get(key)
    assert entry is not None
    cache._entries[key] = type(entry)(
        result=entry.result,
        stored_at=datetime.now(UTC) - timedelta(seconds=2),
    )

    second, metadata = service.search_flights(one_way_request)

    assert second.data_status is FlightDataStatus.LIVE
    assert second.retrieved_at >= first.retrieved_at
    assert metadata.cache_status == "miss"


def test_normalized_cache_key(one_way_request: FlightSearchRequest) -> None:
    key = FlightCache.cache_key(one_way_request)
    assert key == "BOM|DXB|2026-12-01|oneway|2|ECONOMY|INR"


def test_fake_airport_resolver() -> None:
    resolver = FakeAirportCodeResolver()
    assert resolver.resolve("Mumbai") == "BOM"
    assert resolver.resolve("DXB") == "DXB"


@pytest.mark.asyncio
async def test_mcp_tool_contract(one_way_request: FlightSearchRequest) -> None:
    from mcp import Client

    service = FlightService(
        flight_provider=FakeFlightProvider(),
        cache=FlightCache(),
    )
    server = create_flights_mcp_server(service)

    async with Client(server) as client:
        tool_result = await client.call_tool(
            "search_flights",
            {
                "origin": one_way_request.origin,
                "destination": one_way_request.destination,
                "departure_date": one_way_request.departure_date.isoformat(),
                "travelers": one_way_request.travelers,
                "currency": one_way_request.currency,
            },
        )

    payload = tool_result.structured_content
    assert payload["data_status"] == FlightDataStatus.LIVE.value
    assert payload["offers"]
