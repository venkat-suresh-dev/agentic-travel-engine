"""Shared itinerary test fixtures."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from app.budget.engine import BudgetEngine
from app.budget.schemas import BudgetResult
from app.domain.trip_request import TripRequest
from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.schemas import CandidateDayPlan, ItinerarySelectionCandidate
from mcp_tools.distance.schemas import (
    DistanceDataStatus,
    DistanceMatrixResult,
    DistanceRoute,
    LocationPoint,
    TravelMode,
)
from mcp_tools.flights.schemas import (
    CabinClass,
    FlightDataStatus,
    FlightOffer,
    FlightSearchResult,
)
from mcp_tools.hotels.schemas import (
    HotelDataStatus,
    HotelOffer,
    HotelSearchResult,
    MoneyAmount,
)
from mcp_tools.places.schemas import (
    AttractionPlace,
    AttractionSearchResult,
    PlacesDataStatus,
    RestaurantPlace,
    RestaurantSearchResult,
)
from mcp_tools.weather.schemas import (
    DailyForecast,
    WeatherDataStatus,
    WeatherForecastResult,
)

START_DATE = date(2026, 9, 1)


def example_trip_request(*, duration_days: int = 5) -> TripRequest:
    return TripRequest(
        destination="Dubai",
        start_date=START_DATE,
        duration_days=duration_days,
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        departure_city="Mumbai",
    )


def example_attraction_search() -> AttractionSearchResult:
    return AttractionSearchResult(
        source="google_places",
        retrieved_at=datetime.now(UTC),
        data_status=PlacesDataStatus.LIVE,
        attractions=[
            AttractionPlace(
                place_id="places/museum",
                name="Dubai Museum",
                address="Al Fahidi",
                latitude=25.2632,
                longitude=55.2972,
                primary_type="museum",
                rating=4.5,
                user_rating_count=1000,
            ),
            AttractionPlace(
                place_id="places/park",
                name="Zabeel Park",
                address="Zabeel",
                latitude=25.2285,
                longitude=55.3073,
                primary_type="park",
                rating=4.4,
                user_rating_count=800,
            ),
            AttractionPlace(
                place_id="places/mall",
                name="Dubai Mall",
                address="Downtown",
                latitude=25.1972,
                longitude=55.2796,
                primary_type="shopping_mall",
                rating=4.7,
                user_rating_count=5000,
            ),
        ],
    )


def example_restaurant_search() -> RestaurantSearchResult:
    return RestaurantSearchResult(
        source="google_places",
        retrieved_at=datetime.now(UTC),
        data_status=PlacesDataStatus.LIVE,
        restaurants=[
            RestaurantPlace(
                place_id="places/restaurant-a",
                name="Restaurant A",
                address="Downtown",
                latitude=25.1980,
                longitude=55.2800,
                primary_type="restaurant",
                rating=4.3,
                user_rating_count=200,
            ),
            RestaurantPlace(
                place_id="places/restaurant-b",
                name="Restaurant B",
                address="Marina",
                latitude=25.0800,
                longitude=55.1400,
                primary_type="restaurant",
                rating=4.1,
                user_rating_count=150,
            ),
        ],
    )


def example_weather_forecast(
    *,
    rainy_day: int | None = None,
    duration_days: int = 5,
) -> WeatherForecastResult:
    forecast: list[DailyForecast] = []
    for day_index in range(duration_days):
        day_date = START_DATE + timedelta(days=day_index)
        precip = 70 if rainy_day == day_index + 1 else 10
        forecast.append(
            DailyForecast(
                date=day_date,
                temperature_max_c=38.0,
                temperature_min_c=28.0,
                precipitation_probability_max=precip,
                weather_summary="Rain showers" if precip >= 50 else "Clear sky",
                weather_code=61 if precip >= 50 else 0,
            )
        )
    return WeatherForecastResult(
        location="Dubai",
        latitude=25.2048,
        longitude=55.2708,
        source="open_meteo",
        retrieved_at=datetime.now(UTC),
        data_status=WeatherDataStatus.LIVE,
        forecast=forecast,
    )


def example_distance_matrix() -> DistanceMatrixResult:
    museum = LocationPoint(name="Museum", latitude=25.2632, longitude=55.2972)
    park = LocationPoint(name="Park", latitude=25.2285, longitude=55.3073)
    mall = LocationPoint(name="Mall", latitude=25.1972, longitude=55.2796)
    restaurant = LocationPoint(name="Restaurant", latitude=25.1980, longitude=55.2800)
    routes = [
        DistanceRoute(
            origin=museum,
            destination=park,
            distance_meters=4200,
            duration_seconds=900,
            travel_mode=TravelMode.DRIVING,
        ),
        DistanceRoute(
            origin=park,
            destination=mall,
            distance_meters=5100,
            duration_seconds=1100,
            travel_mode=TravelMode.DRIVING,
        ),
        DistanceRoute(
            origin=mall,
            destination=restaurant,
            distance_meters=300,
            duration_seconds=180,
            travel_mode=TravelMode.DRIVING,
        ),
        DistanceRoute(
            origin=museum,
            destination=mall,
            distance_meters=8000,
            duration_seconds=1500,
            travel_mode=TravelMode.DRIVING,
        ),
    ]
    return DistanceMatrixResult(
        source="google_distance_matrix",
        retrieved_at=datetime.now(UTC),
        data_status=DistanceDataStatus.LIVE,
        travel_mode=TravelMode.DRIVING,
        routes=routes,
    )


def example_flight_search() -> FlightSearchResult:
    departure = datetime.combine(START_DATE, time(8, 0), tzinfo=UTC)
    arrival = departure + timedelta(hours=3)
    return FlightSearchResult(
        source="amadeus",
        retrieved_at=datetime.now(UTC),
        data_status=FlightDataStatus.LIVE,
        offers=[
            FlightOffer(
                offer_id="flight-offer-1",
                carrier="EK",
                origin="BOM",
                destination="DXB",
                departure_at=departure,
                arrival_at=arrival,
                duration="PT3H",
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                price_amount=Decimal("45000"),
                price_currency="INR",
                itineraries=[],
            )
        ],
    )


def example_hotel_search() -> HotelSearchResult:
    return HotelSearchResult(
        source="amadeus",
        retrieved_at=datetime.now(UTC),
        data_status=HotelDataStatus.LIVE,
        hotels=[
            HotelOffer(
                hotel_id="hotel-1",
                name="Downtown Hotel",
                location="Dubai",
                check_in=START_DATE,
                check_out=START_DATE + timedelta(days=5),
                latitude=25.2000,
                longitude=55.2700,
                total_price=MoneyAmount(amount=Decimal("2250"), currency="INR"),
            )
        ],
    )


def example_budget_result() -> BudgetResult:
    from app.budget.builder import build_budget_inputs

    trip_request = example_trip_request()
    inputs = build_budget_inputs(
        trip_request,
        flight_search=example_flight_search(),
        hotel_search=example_hotel_search(),
    )
    return BudgetEngine().calculate(inputs)


def example_itinerary_context(
    *,
    duration_days: int = 5,
    rainy_day: int | None = None,
) -> ItineraryBuildContext:
    return ItineraryBuildContext(
        trip_request=example_trip_request(duration_days=duration_days),
        weather_forecast=example_weather_forecast(
            rainy_day=rainy_day,
            duration_days=duration_days,
        ),
        flight_search=example_flight_search(),
        hotel_search=example_hotel_search(),
        distance_matrix=example_distance_matrix(),
        restaurant_search=example_restaurant_search(),
        attraction_search=example_attraction_search(),
        currency_conversion=None,
        budget_result=example_budget_result(),
        retrieved_context=None,
    )


def example_candidate(*, duration_days: int = 5) -> ItinerarySelectionCandidate:
    attraction_ids = [
        place.place_id for place in example_attraction_search().attractions
    ]
    restaurant_ids = [
        place.place_id for place in example_restaurant_search().restaurants
    ]
    days: list[CandidateDayPlan] = []
    for day_number in range(1, duration_days + 1):
        days.append(
            CandidateDayPlan(
                day_number=day_number,
                attraction_source_ids=[
                    attraction_ids[day_number % len(attraction_ids)]
                ],
                restaurant_source_id=restaurant_ids[
                    (day_number - 1) % len(restaurant_ids)
                ],
            )
        )
    return ItinerarySelectionCandidate(days=days)


def fast_assumptions() -> SchedulingAssumptions:
    return SchedulingAssumptions(
        museum_duration_minutes=30,
        meal_duration_minutes=30,
        short_attraction_duration_minutes=30,
        default_attraction_duration_minutes=30,
        travel_buffer_minutes=5,
    )
