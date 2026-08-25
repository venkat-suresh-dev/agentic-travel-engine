"""Materialize a full itinerary from a structured candidate."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from mcp_tools.currency.schemas import quantize_money

from app.budget.schemas import PriceDataKind
from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog, GroundedFlight, GroundedHotel
from app.itinerary.clustering import order_attractions_by_proximity
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.schemas import (
    CandidateDayPlan,
    ItemCost,
    Itinerary,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemCategory,
    ItinerarySelectionCandidate,
    MealSuggestion,
    TravelLeg,
)
from app.itinerary.travel import TravelTimeEstimator


def materialize_itinerary(
    candidate: ItinerarySelectionCandidate,
    *,
    context: ItineraryBuildContext,
    catalog: GroundedCatalog,
    assumptions: SchedulingAssumptions | None = None,
) -> Itinerary:
    scheduling = assumptions or SchedulingAssumptions()
    estimator = TravelTimeEstimator(context.distance_matrix, scheduling)
    currency = context.budget_result.currency

    infrastructure = _build_infrastructure_items(context, catalog, currency)
    days: list[ItineraryDay] = []
    total = Decimal("0")

    for day_plan in sorted(candidate.days, key=lambda item: item.day_number):
        day_date = _day_date(context, day_plan.day_number)
        ordered_attractions = order_attractions_by_proximity(
            day_plan.attraction_source_ids,
            catalog,
            estimator,
        )
        items, legs = _build_day_timeline(
            day_plan=day_plan,
            day_date=day_date,
            ordered_attractions=ordered_attractions,
            catalog=catalog,
            estimator=estimator,
            assumptions=scheduling,
            currency=currency,
        )
        meal_cursor = _cursor_after_last(items, legs, day_date, scheduling)
        restaurant = catalog.restaurants[day_plan.restaurant_source_id]
        if items:
            meal_leg, meal_cursor = _build_travel_leg(
                previous_item=items[-1],
                next_lat=restaurant.latitude,
                next_lng=restaurant.longitude,
                day_number=day_plan.day_number,
                cursor=meal_cursor,
                estimator=estimator,
                assumptions=scheduling,
                leg_index=len(legs),
            )
            legs.append(meal_leg)
        meal_item = _build_restaurant_item(
            day_plan.restaurant_source_id,
            day_number=day_plan.day_number,
            day_date=day_date,
            start_time=meal_cursor.time(),
            catalog=catalog,
            assumptions=scheduling,
            currency=currency,
        )
        if legs and legs[-1].to_item_id.startswith("pending-"):
            legs[-1] = legs[-1].model_copy(update={"to_item_id": meal_item.item_id})
        items.append(meal_item)
        subtotal = _sum_item_costs(items)
        total += subtotal
        days.append(
            ItineraryDay(
                day_number=day_plan.day_number,
                date=day_date,
                items=items,
                travel_legs=legs,
                meal=MealSuggestion(day_number=day_plan.day_number, item=meal_item),
                subtotal=quantize_money(subtotal),
                currency=currency,
            )
        )

    return Itinerary(
        days=days,
        infrastructure_items=infrastructure,
        currency=currency,
        total_estimated_cost=quantize_money(total),
        budget_currency=context.budget_result.currency,
        budget_amount=context.budget_result.budget_amount,
        budget_total_cost=context.budget_result.total_cost,
        budget_remaining=context.budget_result.remaining,
    )


def _build_day_timeline(
    *,
    day_plan: CandidateDayPlan,
    day_date: date | None,
    ordered_attractions: list[str],
    catalog: GroundedCatalog,
    estimator: TravelTimeEstimator,
    assumptions: SchedulingAssumptions,
    currency: str,
) -> tuple[list[ItineraryItem], list[TravelLeg]]:
    items: list[ItineraryItem] = []
    legs: list[TravelLeg] = []
    cursor = datetime.combine(day_date or date.today(), assumptions.day_start_time)

    previous_item: ItineraryItem | None = None
    for index, attraction_id in enumerate(ordered_attractions):
        attraction = catalog.attractions[attraction_id]
        if previous_item is not None:
            leg, cursor = _build_travel_leg(
                previous_item=previous_item,
                next_lat=attraction.latitude,
                next_lng=attraction.longitude,
                day_number=day_plan.day_number,
                cursor=cursor,
                estimator=estimator,
                assumptions=assumptions,
                leg_index=index,
            )
            legs.append(leg)

        duration = _attraction_duration_minutes(attraction.primary_type, assumptions)
        start = cursor.time()
        cursor += timedelta(minutes=duration)
        end = cursor.time()
        item = ItineraryItem(
            item_id=f"day{day_plan.day_number}-attraction-{index}",
            day_number=day_plan.day_number,
            date=day_date,
            start_time=start,
            end_time=end,
            category=ItineraryItemCategory.ATTRACTION,
            title=attraction.name,
            description=None,
            location_name=attraction.name,
            latitude=attraction.latitude,
            longitude=attraction.longitude,
            cost=ItemCost(
                amount=quantize_money(assumptions.estimated_attraction_cost),
                currency=currency,
                is_estimate=True,
                data_kind=PriceDataKind.ESTIMATED,
            ),
            source=attraction.source,
            source_id=attraction.place_id,
            data_status=attraction.data_status,
        )
        if legs and legs[-1].to_item_id.startswith("pending-"):
            legs[-1] = legs[-1].model_copy(update={"to_item_id": item.item_id})
        items.append(item)
        previous_item = item

    return items, legs


def _build_restaurant_item(
    restaurant_id: str,
    *,
    day_number: int,
    day_date: date | None,
    start_time: time,
    catalog: GroundedCatalog,
    assumptions: SchedulingAssumptions,
    currency: str,
) -> ItineraryItem:
    restaurant = catalog.restaurants[restaurant_id]
    start_dt = datetime.combine(day_date or date.today(), start_time)
    end_dt = start_dt + timedelta(minutes=assumptions.meal_duration_minutes)
    return ItineraryItem(
        item_id=f"day{day_number}-meal",
        day_number=day_number,
        date=day_date,
        start_time=start_dt.time(),
        end_time=end_dt.time(),
        category=ItineraryItemCategory.RESTAURANT,
        title=restaurant.name,
        description="Meal suggestion",
        location_name=restaurant.name,
        latitude=restaurant.latitude,
        longitude=restaurant.longitude,
        cost=ItemCost(
            amount=quantize_money(assumptions.estimated_meal_cost),
            currency=currency,
            is_estimate=True,
            data_kind=PriceDataKind.ESTIMATED,
        ),
        source=restaurant.source,
        source_id=restaurant.place_id,
        data_status=restaurant.data_status,
    )


def _build_travel_leg(
    *,
    previous_item: ItineraryItem,
    next_lat: float,
    next_lng: float,
    day_number: int,
    cursor: datetime,
    estimator: TravelTimeEstimator,
    assumptions: SchedulingAssumptions,
    leg_index: int,
) -> tuple[TravelLeg, datetime]:
    estimate = estimator.estimate(
        origin_lat=previous_item.latitude or 0.0,
        origin_lng=previous_item.longitude or 0.0,
        destination_lat=next_lat,
        destination_lng=next_lng,
    )
    travel_seconds = estimate.duration_seconds + assumptions.travel_buffer_minutes * 60
    start = cursor.time()
    cursor += timedelta(seconds=travel_seconds)
    end = cursor.time()
    leg = TravelLeg(
        leg_id=f"day{day_number}-travel-{leg_index}-{start.strftime('%H%M%S')}",
        from_item_id=previous_item.item_id,
        to_item_id=f"pending-{leg_index}",
        day_number=day_number,
        start_time=start,
        end_time=end,
        distance_meters=estimate.distance_meters,
        duration_seconds=estimate.duration_seconds,
        travel_mode=estimate.travel_mode,
        source=estimate.source,
        data_status=estimate.data_status,
    )
    return leg, cursor


def _build_infrastructure_items(
    context: ItineraryBuildContext,
    catalog: GroundedCatalog,
    currency: str,
) -> list[ItineraryItem]:
    items: list[ItineraryItem] = []
    if catalog.flights:
        flight = min(catalog.flights.values(), key=lambda item: item.departure_at)
        items.append(_flight_item(flight, currency))
    if catalog.hotels:
        hotel = next(iter(catalog.hotels.values()))
        items.extend(_hotel_items(hotel, currency))
    return items


def _flight_item(flight: GroundedFlight, currency: str) -> ItineraryItem:
    return ItineraryItem(
        item_id=f"flight-{flight.offer_id}",
        day_number=None,
        date=flight.departure_at.date(),
        start_time=flight.departure_at.time(),
        end_time=flight.arrival_at.time(),
        category=ItineraryItemCategory.FLIGHT,
        title=flight.title,
        description="Outbound flight",
        location_name=None,
        latitude=None,
        longitude=None,
        cost=ItemCost(
            amount=quantize_money(flight.price_amount) if flight.price_amount else None,
            currency=flight.price_currency or currency,
            is_estimate=False,
            data_kind=flight.data_status,
        ),
        source=flight.source,
        source_id=flight.offer_id,
        data_status=flight.data_status,
    )


def _hotel_items(hotel: GroundedHotel, currency: str) -> list[ItineraryItem]:
    check_in = time(15, 0)
    check_out = time(11, 0)
    return [
        ItineraryItem(
            item_id=f"hotel-checkin-{hotel.hotel_id}",
            day_number=None,
            date=hotel.check_in,
            start_time=check_in,
            end_time=time(15, 30),
            category=ItineraryItemCategory.HOTEL,
            title=f"{hotel.name} check-in",
            description="Accommodation check-in",
            location_name=hotel.name,
            latitude=hotel.latitude,
            longitude=hotel.longitude,
            cost=ItemCost(
                amount=quantize_money(hotel.total_amount)
                if hotel.total_amount
                else None,
                currency=hotel.total_currency or currency,
                is_estimate=False,
                data_kind=hotel.data_status,
            ),
            source=hotel.source,
            source_id=hotel.hotel_id,
            data_status=hotel.data_status,
        ),
        ItineraryItem(
            item_id=f"hotel-checkout-{hotel.hotel_id}",
            day_number=None,
            date=hotel.check_out,
            start_time=check_out,
            end_time=time(11, 30),
            category=ItineraryItemCategory.HOTEL,
            title=f"{hotel.name} check-out",
            description="Accommodation check-out",
            location_name=hotel.name,
            latitude=hotel.latitude,
            longitude=hotel.longitude,
            cost=ItemCost(
                amount=None,
                currency=hotel.total_currency or currency,
                is_estimate=False,
                data_kind=PriceDataKind.UNAVAILABLE,
            ),
            source=hotel.source,
            source_id=hotel.hotel_id,
            data_status=hotel.data_status,
        ),
    ]


def _day_date(context: ItineraryBuildContext, day_number: int) -> date | None:
    start = context.trip_request.start_date
    if start is None:
        return None
    return start + timedelta(days=day_number - 1)


def _attraction_duration_minutes(
    primary_type: str | None,
    assumptions: SchedulingAssumptions,
) -> int:
    if primary_type in assumptions.indoor_attraction_types:
        return assumptions.museum_duration_minutes
    if primary_type in {"park", "historical_landmark"}:
        return assumptions.short_attraction_duration_minutes
    return assumptions.default_attraction_duration_minutes


def _cursor_after_last(
    items: list[ItineraryItem],
    legs: list[TravelLeg],
    day_date: date | None,
    assumptions: SchedulingAssumptions,
) -> datetime:
    if not items:
        return datetime.combine(day_date or date.today(), assumptions.day_start_time)
    last_end = items[-1].end_time
    if legs:
        last_end = legs[-1].end_time
    return datetime.combine(day_date or date.today(), last_end)


def _sum_item_costs(items: list[ItineraryItem]) -> Decimal:
    total = Decimal("0")
    for item in items:
        if (
            item.cost.amount is not None
            and item.cost.data_kind != PriceDataKind.UNAVAILABLE
        ):
            total += item.cost.amount
    return total
