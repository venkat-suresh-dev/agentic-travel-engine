"""Grounded entity catalog for itinerary composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from mcp_tools.flights.schemas import FlightDataStatus
from mcp_tools.hotels.schemas import HotelDataStatus
from mcp_tools.places.reference.schemas import SignificanceTier
from mcp_tools.places.schemas import (
    AttractionPlace,
    PlacesDataStatus,
)
from mcp_tools.weather.schemas import DailyForecast, WeatherDataStatus

from app.budget.schemas import PriceDataKind
from app.itinerary.context import ItineraryBuildContext


@dataclass(frozen=True, slots=True)
class GroundedAttraction:
    place_id: str
    name: str
    latitude: float
    longitude: float
    primary_type: str | None
    source: str
    data_status: PriceDataKind
    is_indoor: bool
    significance_tier: SignificanceTier = SignificanceTier.POI
    quality_score: float | None = None
    reference_page_id: int | None = None
    reference_source: str | None = None
    rating: float | None = None
    price_level: str | None = None
    address: str | None = None
    user_rating_count: int | None = None


@dataclass(frozen=True, slots=True)
class GroundedRestaurant:
    place_id: str
    name: str
    latitude: float
    longitude: float
    source: str
    data_status: PriceDataKind
    rating: float | None = None
    price_level: str | None = None
    primary_type: str | None = None
    address: str | None = None
    user_rating_count: int | None = None


@dataclass(frozen=True, slots=True)
class GroundedFlight:
    offer_id: str
    title: str
    carrier: str
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration: str
    stops: int
    source: str
    data_status: PriceDataKind
    price_amount: Decimal | None
    price_currency: str | None


@dataclass(frozen=True, slots=True)
class GroundedHotel:
    hotel_id: str
    name: str
    check_in: date
    check_out: date
    latitude: float | None
    longitude: float | None
    source: str
    data_status: PriceDataKind
    total_amount: Decimal | None
    total_currency: str | None


@dataclass
class GroundedCatalog:
    attractions: dict[str, GroundedAttraction] = field(default_factory=dict)
    restaurants: dict[str, GroundedRestaurant] = field(default_factory=dict)
    flights: dict[str, GroundedFlight] = field(default_factory=dict)
    hotels: dict[str, GroundedHotel] = field(default_factory=dict)
    weather_by_day: dict[int, DailyForecast] = field(default_factory=dict)
    indoor_attraction_types: frozenset[str] = frozenset(
        {"museum", "art_gallery", "shopping_mall"}
    )

    def attraction_ids(self) -> list[str]:
        return list(self.attractions.keys())

    def restaurant_ids(self) -> list[str]:
        return list(self.restaurants.keys())


def build_grounded_catalog(
    context: ItineraryBuildContext,
    *,
    indoor_types: frozenset[str] | None = None,
) -> GroundedCatalog:
    catalog = GroundedCatalog(
        indoor_attraction_types=indoor_types
        or GroundedCatalog().indoor_attraction_types
    )
    _index_attractions(context, catalog)
    _index_restaurants(context, catalog)
    _index_flights(context, catalog)
    _index_hotels(context, catalog)
    _index_weather(context, catalog)
    from app.itinerary.reference.fusion import fuse_reference_landmarks

    fuse_reference_landmarks(catalog, context)
    return catalog


def _index_attractions(
    context: ItineraryBuildContext, catalog: GroundedCatalog
) -> None:
    search = context.attraction_search
    if search is None or search.data_status == PlacesDataStatus.UNAVAILABLE:
        return
    status = _places_status(search.data_status.value)
    for place in search.attractions:
        primary_type = _normalize_primary_type(place.primary_type, place.name)
        catalog.attractions[place.place_id] = GroundedAttraction(
            place_id=place.place_id,
            name=place.name,
            latitude=place.latitude,
            longitude=place.longitude,
            primary_type=primary_type,
            source=search.source,
            data_status=status,
            is_indoor=_is_indoor_type(primary_type, catalog.indoor_attraction_types),
            rating=place.rating,
            price_level=place.price_level.value if place.price_level else None,
            address=place.address,
            user_rating_count=place.user_rating_count,
        )


def _index_restaurants(
    context: ItineraryBuildContext, catalog: GroundedCatalog
) -> None:
    search = context.restaurant_search
    if search is None or search.data_status == PlacesDataStatus.UNAVAILABLE:
        return
    status = _places_status(search.data_status.value)
    for place in search.restaurants:
        catalog.restaurants[place.place_id] = GroundedRestaurant(
            place_id=place.place_id,
            name=place.name,
            latitude=place.latitude,
            longitude=place.longitude,
            source=search.source,
            data_status=status,
            rating=place.rating,
            price_level=place.price_level.value if place.price_level else None,
            primary_type=place.primary_type,
            address=place.address,
            user_rating_count=place.user_rating_count,
        )


def _index_flights(context: ItineraryBuildContext, catalog: GroundedCatalog) -> None:
    search = context.flight_search
    if search is None or search.data_status == FlightDataStatus.UNAVAILABLE:
        return
    status = _flight_status(search.data_status.value)
    for offer in search.offers:
        catalog.flights[offer.offer_id] = GroundedFlight(
            offer_id=offer.offer_id,
            title=f"{offer.carrier} {offer.origin}→{offer.destination}",
            carrier=offer.carrier,
            origin=offer.origin,
            destination=offer.destination,
            departure_at=offer.departure_at,
            arrival_at=offer.arrival_at,
            duration=offer.duration,
            stops=offer.stops,
            source=search.source,
            data_status=status,
            price_amount=offer.price_amount,
            price_currency=offer.price_currency,
        )


def _index_hotels(context: ItineraryBuildContext, catalog: GroundedCatalog) -> None:
    search = context.hotel_search
    if search is None or search.data_status == HotelDataStatus.UNAVAILABLE:
        return
    status = _hotel_status(search.data_status.value)
    for offer in search.hotels:
        total_amount = offer.total_price.amount if offer.total_price else None
        total_currency = offer.total_price.currency if offer.total_price else None
        catalog.hotels[offer.hotel_id] = GroundedHotel(
            hotel_id=offer.hotel_id,
            name=offer.name,
            check_in=offer.check_in,
            check_out=offer.check_out,
            latitude=offer.latitude,
            longitude=offer.longitude,
            source=search.source,
            data_status=status,
            total_amount=total_amount,
            total_currency=total_currency,
        )


def _index_weather(context: ItineraryBuildContext, catalog: GroundedCatalog) -> None:
    forecast = context.weather_forecast
    if forecast is None or forecast.data_status == WeatherDataStatus.UNAVAILABLE:
        return
    start = context.trip_request.start_date
    for index, day in enumerate(forecast.forecast, start=1):
        catalog.weather_by_day[index] = day
        if start is not None and day.date == start:
            continue


def _is_indoor(place: AttractionPlace, indoor_types: frozenset[str]) -> bool:
    if place.primary_type is None:
        return False
    return _is_indoor_type(place.primary_type, indoor_types)


def _is_indoor_type(primary_type: str | None, indoor_types: frozenset[str]) -> bool:
    if primary_type is None:
        return False
    return primary_type in indoor_types


def _normalize_primary_type(raw_type: str | None, name: str) -> str | None:
    if raw_type:
        lowered = raw_type.lower()
        if "museum" in lowered:
            return "museum"
        if "gallery" in lowered or "culture" in lowered:
            return "art_gallery"
        if "park" in lowered or "garden" in lowered:
            return "park"
        if "heritage" in lowered or "historical" in lowered:
            return "historical_landmark"
        if "worship" in lowered or "mosque" in lowered or "temple" in lowered:
            return "place_of_worship"
        if "mall" in lowered or "shop" in lowered:
            return "shopping_mall"
        if "zoo" in lowered:
            return "zoo"
        if "theme_park" in lowered or "amusement" in lowered:
            return "amusement_park"
        if "tourism" in lowered or "sight" in lowered or "attraction" in lowered:
            return "tourist_attraction"

    name_lower = name.lower()
    if any(token in name_lower for token in ("museum", "gallery")):
        return "museum"
    if any(token in name_lower for token in ("park", "garden", "beach")):
        return "park"
    if any(token in name_lower for token in ("mosque", "temple", "church")):
        return "place_of_worship"
    if any(token in name_lower for token in ("souq", "souk", "bazaar", "market")):
        return "historical_landmark"
    if any(token in name_lower for token in ("mall", "shopping")):
        return "shopping_mall"
    if any(token in name_lower for token in ("tower", "frame", "fountain", "marina")):
        return "tourist_attraction"
    return raw_type


def _places_status(value: str) -> PriceDataKind:
    if value == "cached":
        return PriceDataKind.CACHED
    return PriceDataKind.LIVE


def _flight_status(value: str) -> PriceDataKind:
    if value == "cached":
        return PriceDataKind.CACHED
    return PriceDataKind.LIVE


def _hotel_status(value: str) -> PriceDataKind:
    if value == "cached":
        return PriceDataKind.CACHED
    return PriceDataKind.LIVE
