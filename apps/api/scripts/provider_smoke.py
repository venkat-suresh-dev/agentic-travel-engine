"""Live provider smoke checks for local demo environments.

Run with: uv run python scripts/provider_smoke.py
Never prints secret values.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import date, timedelta
from decimal import Decimal

from mcp_tools.currency.schemas import CurrencyConversionRequest
from mcp_tools.distance.schemas import DistanceMatrixRequest, LocationPoint, TravelMode
from mcp_tools.flights.schemas import CabinClass, FlightSearchRequest
from mcp_tools.places.schemas import (
    AttractionSearchRequest,
    RestaurantSearchRequest,
    SearchLocation,
)
from mcp_tools.weather.cache import WeatherCache
from mcp_tools.weather.geocoding.open_meteo import OpenMeteoGeocodingProvider
from mcp_tools.weather.providers.open_meteo import OpenMeteoWeatherProvider
from mcp_tools.weather.schemas import WeatherForecastRequest
from mcp_tools.weather.service import WeatherService

from app.core.config import settings
from app.domain.trip_request import TripRequest
from app.llm.factory import build_llm_adapter
from app.rag.embeddings import build_embedding_provider
from app.tools.currency_factory import build_currency_tool
from app.tools.distance_factory import build_distance_tool, build_location_resolver
from app.tools.flights_factory import build_airport_resolver, build_flight_service
from app.tools.flights_request import build_flight_search_request
from app.tools.hotels_factory import build_city_resolver, build_hotel_service
from app.tools.hotels_request import build_hotel_search_request
from app.tools.places_factory import build_places_service
from app.tools.weather import WeatherTool


def _status(name: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "FAIL"
    suffix = f" ({detail})" if detail else ""
    print(f"{name}: {mark}{suffix}")


def main() -> int:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    failures = 0

    print("Configuration (names only):")
    print(f"  LLM_PROVIDER={settings.llm_provider}")
    print(f"  GROQ_API_KEY={'configured' if settings.groq_api_key else 'missing'}")
    print(f"  EMBEDDING_PROVIDER={settings.rag_embedding_provider}")
    print(f"  GEMINI_API_KEY={'configured' if settings.gemini_api_key else 'missing'}")
    print(f"  FLIGHTS_PROVIDER={settings.flights_provider}")
    print(f"  SERPAPI_API_KEY={'configured' if settings.serpapi_api_key else 'missing'}")
    print(f"  HOTELS_PROVIDER={settings.hotels_provider}")
    print(
        f"  STAYINGAPI_API_KEY={'configured' if settings.stayingapi_api_key else 'missing'}"
    )
    print(f"  PLACES_PROVIDER={settings.places_provider}")
    print(f"  GEOAPIFY_API_KEY={'configured' if settings.geoapify_api_key else 'missing'}")
    print(
        "  OPENROUTESERVICE_API_KEY="
        f"{'configured' if settings.openrouteservice_api_key else 'missing'}"
    )
    print(f"  CLERK_SECRET_KEY={'configured' if settings.clerk_secret_key else 'missing'}")
    print()

    trip = TripRequest(
        departure_city="Mumbai",
        destination="Dubai",
        start_date=date.today() + timedelta(days=30),
        duration_days=5,
        travelers=2,
        budget_amount=150000,
        budget_currency="INR",
    )

    try:
        adapter = build_llm_adapter()
        result = adapter.generate_structured(
            system_prompt="Extract trip requirements as JSON.",
            user_prompt=(
                "Plan a 5-day trip to Dubai for 2 people under 150000 INR from Mumbai "
                "starting 2026-10-01."
            ),
            response_model=TripRequest,
        )
        ok = result.data.destination is not None
        _status("groq-structured", ok, result.data.destination or "")
        failures += 0 if ok else 1
    except Exception as exc:
        _status("groq-structured", False, str(exc)[:120])
        failures += 1

    async def _embed() -> int:
        provider = build_embedding_provider(settings)
        vector = await provider.embed_query("Dubai travel tips")
        return len(vector)

    try:
        dim = asyncio.run(_embed())
        ok = dim == settings.rag_embedding_dimensions
        _status("gemini-embedding", ok, f"dim={dim}")
        failures += 0 if ok else 1
    except Exception as exc:
        _status("gemini-embedding", False, str(exc)[:120])
        failures += 1

    try:
        flight_req = build_flight_search_request(trip, build_airport_resolver())
        result, _ = build_flight_service().search_flights(flight_req)
        ok = len(result.offers) > 0
        _status(
            "serpapi-flights",
            ok,
            f"offers={len(result.offers)} status={result.data_status}",
        )
        failures += 0 if ok else 1
    except Exception as exc:
        _status("serpapi-flights", False, str(exc)[:120])
        failures += 1

    try:
        hotel_req = build_hotel_search_request(trip, build_city_resolver())
        result, _ = build_hotel_service().search_hotels(hotel_req)
        ok = len(result.hotels) > 0
        _status(
            "stayingapi-hotels",
            ok,
            f"hotels={len(result.hotels)} source={result.source}",
        )
        failures += 0 if ok else 1
    except Exception as exc:
        _status("stayingapi-hotels", False, str(exc)[:120])
        failures += 1

    try:
        location = SearchLocation(name="Dubai", latitude=25.2048, longitude=55.2708)
        places = build_places_service()
        restaurants, _ = places.search_restaurants(
            RestaurantSearchRequest(location=location, max_results=5)
        )
        attractions, _ = places.search_attractions(
            AttractionSearchRequest(location=location, max_results=5)
        )
        ok = len(restaurants.restaurants) > 0 and len(attractions.attractions) > 0
        _status(
            "geoapify-places",
            ok,
            (
                f"restaurants={len(restaurants.restaurants)} "
                f"attractions={len(attractions.attractions)}"
            ),
        )
        failures += 0 if ok else 1
    except Exception as exc:
        _status("geoapify-places", False, str(exc)[:120])
        failures += 1

    try:
        coords = build_location_resolver().resolve("Dubai")
        ok = coords.latitude != 0
        _status("geoapify-geocoding", ok, f"lat={coords.latitude:.4f}")
        failures += 0 if ok else 1
    except Exception as exc:
        _status("geoapify-geocoding", False, str(exc)[:120])
        failures += 1

    try:
        service = WeatherService(
            geocoding_provider=OpenMeteoGeocodingProvider(timeout_seconds=5),
            weather_provider=OpenMeteoWeatherProvider(timeout_seconds=5),
            cache=WeatherCache(ttl_seconds=1800),
        )
        tool = WeatherTool(service)
        start = date.today() + timedelta(days=3)
        result, _ = tool.get_forecast(
            WeatherForecastRequest(
                location="Dubai",
                start_date=start,
                end_date=start + timedelta(days=5),
            )
        )
        ok = len(result.forecast) > 0
        _status("open-meteo", ok, f"days={len(result.forecast)}")
        failures += 0 if ok else 1
    except Exception as exc:
        _status("open-meteo", False, str(exc)[:120])
        failures += 1

    try:
        tool = build_distance_tool()
        result, _ = tool.get_distance_matrix(
            DistanceMatrixRequest(
                origins=[
                    LocationPoint(name="Mumbai Airport", latitude=19.0896, longitude=72.8656)
                ],
                destinations=[
                    LocationPoint(name="Dubai Airport", latitude=25.2532, longitude=55.3657)
                ],
                travel_mode=TravelMode.DRIVING,
            )
        )
        ok = len(result.routes) > 0 and result.routes[0].distance_meters > 0
        _status(
            "openrouteservice",
            ok,
            f"meters={result.routes[0].distance_meters if result.routes else 0}",
        )
        failures += 0 if ok else 1
    except Exception as exc:
        _status("openrouteservice", False, str(exc)[:120])
        failures += 1

    try:
        tool = build_currency_tool()
        usd_inr, _ = tool.convert_currency(
            CurrencyConversionRequest(
                base_currency="USD",
                quote_currency="INR",
                amount=Decimal("100"),
            )
        )
        inr_inr, _ = tool.convert_currency(
            CurrencyConversionRequest(
                base_currency="INR",
                quote_currency="INR",
                amount=Decimal("100"),
            )
        )
        ok = usd_inr.converted_amount > 0 and inr_inr.converted_amount == Decimal("100")
        _status(
            "frankfurter",
            ok,
            f"USD->INR converted; INR->INR={inr_inr.converted_amount}",
        )
        failures += 0 if ok else 1
    except Exception as exc:
        _status("frankfurter", False, str(exc)[:120])
        failures += 1

    try:
        flight_req = FlightSearchRequest(
            origin="BOM",
            destination="DXB",
            departure_date=date.today() + timedelta(days=45),
            travelers=2,
            cabin_class=CabinClass.ECONOMY,
            currency="INR",
        )
        service = build_flight_service()
        _, meta1 = service.search_flights(flight_req)
        _, meta2 = service.search_flights(flight_req)
        ok = meta1.cache_status == "miss" and meta2.cache_status == "hit"
        _status(
            "flight-cache",
            ok,
            f"first={meta1.cache_status} second={meta2.cache_status}",
        )
        failures += 0 if ok else 1
    except Exception as exc:
        _status("flight-cache", False, str(exc)[:120])
        failures += 1

    print()
    print(f"Failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
