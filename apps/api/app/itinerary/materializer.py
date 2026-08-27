"""Materialize a full itinerary from a structured candidate."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from mcp_tools.currency.schemas import quantize_money

from app.budget.schemas import BudgetCategory, BudgetResult, PriceDataKind
from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog, GroundedFlight, GroundedHotel
from app.itinerary.clustering import order_attractions_by_proximity
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.diversity.themes import DayTheme
from app.itinerary.quality import disambiguate_title
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
    relaxed_days: frozenset[int] | None = None,
    selected_hotel_id: str | None = None,
    day_themes: dict[int, DayTheme] | None = None,
) -> Itinerary:
    scheduling = assumptions or SchedulingAssumptions()
    estimator = TravelTimeEstimator(context.distance_matrix, scheduling)
    currency = context.budget_result.currency
    relaxed = relaxed_days or frozenset()

    infrastructure = _build_infrastructure_items(
        context, catalog, currency, selected_hotel_id=selected_hotel_id
    )
    days: list[ItineraryDay] = []
    total = Decimal("0")
    used_titles: set[str] = set()

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
            relaxed=day_plan.day_number in relaxed,
            hotel=_selected_hotel(catalog, selected_hotel_id),
            used_titles=used_titles,
        )
        meal_cursor = _cursor_after_last(items, legs, day_date, scheduling)
        restaurant = catalog.restaurants[day_plan.restaurant_source_id]
        is_relaxed = day_plan.day_number in relaxed
        travel_buffer = (
            scheduling.relaxed_travel_buffer_minutes
            if is_relaxed
            else scheduling.travel_buffer_minutes
        )
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
                travel_buffer_minutes=travel_buffer,
            )
            if meal_leg is not None:
                legs.append(meal_leg)
        meal_item = _build_restaurant_item(
            day_plan.restaurant_source_id,
            day_number=day_plan.day_number,
            day_date=day_date,
            start_time=meal_cursor.time(),
            catalog=catalog,
            assumptions=scheduling,
            currency=currency,
            used_titles=used_titles,
        )
        if legs and legs[-1].to_item_id.startswith("pending-"):
            legs[-1] = legs[-1].model_copy(update={"to_item_id": meal_item.item_id})
        items.append(meal_item)
        subtotal = _sum_item_costs(items)
        total += subtotal
        theme = (day_themes or {}).get(day_plan.day_number)
        days.append(
            ItineraryDay(
                day_number=day_plan.day_number,
                date=day_date,
                day_theme=theme.title if theme else None,
                theme_subtitle=theme.subtitle if theme else None,
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
    relaxed: bool = False,
    hotel: GroundedHotel | None = None,
    used_titles: set[str] | None = None,
) -> tuple[list[ItineraryItem], list[TravelLeg]]:
    titles = used_titles if used_titles is not None else set()
    items: list[ItineraryItem] = []
    legs: list[TravelLeg] = []
    start_time = (
        assumptions.relaxed_day_start_time if relaxed else assumptions.day_start_time
    )
    cursor = datetime.combine(day_date or date.today(), start_time)
    previous_item: ItineraryItem | None = None
    travel_buffer = (
        assumptions.relaxed_travel_buffer_minutes
        if relaxed
        else assumptions.travel_buffer_minutes
    )

    if relaxed:
        slow_morning = _build_free_time_item(
            day_number=day_plan.day_number,
            day_date=day_date,
            start_time=cursor.time(),
            duration_minutes=assumptions.free_time_duration_minutes,
            title="Slow morning",
            description="Unscheduled time to ease into the day",
            currency=currency,
            latitude=hotel.latitude if hotel is not None else None,
            longitude=hotel.longitude if hotel is not None else None,
            location_name=hotel.name if hotel is not None else None,
            index=0,
        )
        cursor += timedelta(minutes=assumptions.free_time_duration_minutes)
        items.append(slow_morning)
        previous_item = slow_morning

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
                travel_buffer_minutes=travel_buffer,
            )
            if leg is not None:
                legs.append(leg)

        duration = _attraction_duration_minutes(attraction.primary_type, assumptions)
        start = cursor.time()
        cursor += timedelta(minutes=duration)
        end = cursor.time()
        display_title = disambiguate_title(
            attraction.name,
            address=attraction.address,
            primary_type=attraction.primary_type,
            used_titles=titles,
        )
        titles.add(display_title)
        is_reference = attraction.data_status == PriceDataKind.REFERENCE
        item = ItineraryItem(
            item_id=f"day{day_plan.day_number}-attraction-{index}",
            day_number=day_plan.day_number,
            date=day_date,
            start_time=start,
            end_time=end,
            category=ItineraryItemCategory.ATTRACTION,
            title=display_title,
            description="Reference landmark" if is_reference else None,
            location_name=display_title,
            latitude=attraction.latitude,
            longitude=attraction.longitude,
            cost=(
                ItemCost(
                    amount=None,
                    currency=currency,
                    is_estimate=False,
                    data_kind=PriceDataKind.FREE,
                )
                if is_reference
                else ItemCost(
                    amount=quantize_money(assumptions.estimated_attraction_cost),
                    currency=currency,
                    is_estimate=True,
                    data_kind=PriceDataKind.ESTIMATED,
                )
            ),
            source=attraction.source,
            source_id=attraction.place_id,
            data_status=attraction.data_status,
        )
        if legs and legs[-1].to_item_id.startswith("pending-"):
            legs[-1] = legs[-1].model_copy(update={"to_item_id": item.item_id})
        items.append(item)
        previous_item = item

    if relaxed:
        cafe_start = cursor
        cafe = _build_free_time_item(
            day_number=day_plan.day_number,
            day_date=day_date,
            start_time=cafe_start.time(),
            duration_minutes=assumptions.free_time_duration_minutes,
            title="Cafe / free time",
            description="Unscheduled pause before dinner",
            currency=currency,
            latitude=previous_item.latitude if previous_item is not None else None,
            longitude=previous_item.longitude if previous_item is not None else None,
            location_name=previous_item.location_name
            if previous_item is not None
            else None,
            index=1,
        )
        cursor += timedelta(minutes=assumptions.free_time_duration_minutes)
        items.append(cafe)
        previous_item = cafe

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
    used_titles: set[str] | None = None,
) -> ItineraryItem:
    restaurant = catalog.restaurants[restaurant_id]
    titles = used_titles if used_titles is not None else set()
    display_title = disambiguate_title(
        restaurant.name,
        address=restaurant.address,
        primary_type=restaurant.primary_type,
        used_titles=titles,
    )
    titles.add(display_title)
    start_dt = datetime.combine(day_date or date.today(), start_time)
    end_dt = start_dt + timedelta(minutes=assumptions.meal_duration_minutes)
    return ItineraryItem(
        item_id=f"day{day_number}-meal",
        day_number=day_number,
        date=day_date,
        start_time=start_dt.time(),
        end_time=end_dt.time(),
        category=ItineraryItemCategory.RESTAURANT,
        title=display_title,
        description="Meal suggestion",
        location_name=display_title,
        latitude=restaurant.latitude,
        longitude=restaurant.longitude,
        cost=ItemCost(
            amount=quantize_money(
                assumptions.meal_cost_for_price_level(restaurant.price_level)
            ),
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
    travel_buffer_minutes: int | None = None,
) -> tuple[TravelLeg | None, datetime]:
    buffer_minutes = (
        assumptions.travel_buffer_minutes
        if travel_buffer_minutes is None
        else travel_buffer_minutes
    )
    origin_lat = previous_item.latitude
    origin_lng = previous_item.longitude
    if origin_lat is None or origin_lng is None:
        cursor += timedelta(minutes=buffer_minutes)
        return None, cursor
    if origin_lat == next_lat and origin_lng == next_lng:
        cursor += timedelta(minutes=buffer_minutes)
        return None, cursor

    estimate = estimator.estimate(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_lat=next_lat,
        destination_lng=next_lng,
    )
    travel_seconds = estimate.duration_seconds + buffer_minutes * 60
    if travel_seconds <= 0:
        cursor += timedelta(minutes=max(buffer_minutes, 1))
        return None, cursor
    start_dt = cursor
    end_dt = cursor + timedelta(seconds=travel_seconds)
    if end_dt.date() != start_dt.date() or travel_seconds > 3 * 60 * 60:
        cursor = start_dt + timedelta(minutes=max(buffer_minutes, 1))
        return None, cursor
    start = start_dt.time()
    end = end_dt.time()
    cursor = end_dt
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
    selected_hotel_id: str | None = None,
) -> list[ItineraryItem]:
    items: list[ItineraryItem] = []
    budget = context.budget_result
    if catalog.flights:
        flight = min(
            catalog.flights.values(),
            key=lambda item: (
                item.price_amount is None,
                item.price_amount if item.price_amount is not None else Decimal("0"),
            ),
        )
        items.append(_flight_item(flight, currency, budget))
    hotel = _selected_hotel(catalog, selected_hotel_id)
    if hotel is not None:
        items.extend(_hotel_items(hotel, currency, budget))
    return items


def _cost_aligned_to_budget(
    *,
    category: BudgetCategory,
    original_amount: Decimal | None,
    original_currency: str,
    budget: BudgetResult,
    fallback_data_kind: PriceDataKind,
) -> ItemCost:
    """Prefer authoritative budget amounts; preserve provider-native currency."""
    line = next(
        (entry for entry in budget.categories if entry.category == category), None
    )
    original_currency_upper = original_currency.upper()
    if line is not None and line.included_in_total and line.amount is not None:
        source_amount: Decimal | None = None
        source_currency: str | None = None
        if (
            line.source_amount is not None
            and line.source_currency
            and line.source_currency.upper() != line.currency.upper()
        ):
            source_amount = quantize_money(line.source_amount)
            source_currency = line.source_currency.upper()
        elif (
            original_amount is not None
            and original_currency_upper != line.currency.upper()
        ):
            source_amount = quantize_money(original_amount)
            source_currency = original_currency_upper
        return ItemCost(
            amount=line.amount,
            currency=line.currency,
            is_estimate=line.is_estimate,
            data_kind=(
                line.data_kind
                if line.data_kind != PriceDataKind.UNAVAILABLE
                else fallback_data_kind
            ),
            source_amount=source_amount,
            source_currency=source_currency,
        )

    return ItemCost(
        amount=quantize_money(original_amount) if original_amount is not None else None,
        currency=original_currency_upper,
        is_estimate=False,
        data_kind=fallback_data_kind,
        source_amount=None,
        source_currency=None,
    )


def _flight_item(
    flight: GroundedFlight, currency: str, budget: BudgetResult
) -> ItineraryItem:
    original_currency = flight.price_currency or currency
    return ItineraryItem(
        item_id=f"flight-{flight.offer_id}",
        day_number=None,
        date=flight.departure_at.date(),
        start_time=flight.departure_at.time(),
        end_time=flight.arrival_at.time(),
        category=ItineraryItemCategory.FLIGHT,
        title=flight.title,
        description=_flight_description(flight),
        location_name=None,
        latitude=None,
        longitude=None,
        cost=_cost_aligned_to_budget(
            category=BudgetCategory.FLIGHT,
            original_amount=flight.price_amount,
            original_currency=original_currency,
            budget=budget,
            fallback_data_kind=flight.data_status,
        ),
        source=flight.source,
        source_id=flight.offer_id,
        data_status=flight.data_status,
    )


def _flight_description(flight: GroundedFlight) -> str:
    parts = ["Outbound flight"]
    if flight.stops == 0:
        parts.append("Nonstop")
    else:
        stop_label = "stop" if flight.stops == 1 else "stops"
        parts.append(f"{flight.stops} {stop_label}")
    duration = _format_iso_duration(flight.duration)
    if duration:
        parts.append(duration)
    return " · ".join(parts)


def _format_iso_duration(value: str) -> str | None:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value.strip().upper())
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    if minutes:
        return f"{minutes} min"
    return None


def _hotel_items(
    hotel: GroundedHotel, currency: str, budget: BudgetResult
) -> list[ItineraryItem]:
    check_in = time(15, 0)
    check_out = time(11, 0)
    original_currency = hotel.total_currency or currency
    check_in_cost = _cost_aligned_to_budget(
        category=BudgetCategory.HOTEL,
        original_amount=hotel.total_amount,
        original_currency=original_currency,
        budget=budget,
        fallback_data_kind=hotel.data_status,
    )
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
            cost=check_in_cost,
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
                currency=check_in_cost.currency,
                is_estimate=False,
                data_kind=PriceDataKind.UNAVAILABLE,
                source_amount=None,
                source_currency=None,
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
        last_leg_end = max(leg.end_time for leg in legs)
        if last_leg_end > last_end:
            last_end = last_leg_end
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


def _selected_hotel(
    catalog: GroundedCatalog, selected_hotel_id: str | None
) -> GroundedHotel | None:
    if selected_hotel_id and selected_hotel_id in catalog.hotels:
        return catalog.hotels[selected_hotel_id]
    if not catalog.hotels:
        return None
    return min(
        catalog.hotels.values(),
        key=lambda hotel: (
            hotel.total_amount is None,
            hotel.total_amount if hotel.total_amount is not None else Decimal("0"),
        ),
    )


def _build_free_time_item(
    *,
    day_number: int,
    day_date: date | None,
    start_time: time,
    duration_minutes: int,
    title: str,
    description: str,
    currency: str,
    latitude: float | None,
    longitude: float | None,
    location_name: str | None,
    index: int,
) -> ItineraryItem:
    start_dt = datetime.combine(day_date or date.today(), start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return ItineraryItem(
        item_id=f"day{day_number}-free-{index}",
        day_number=day_number,
        date=day_date,
        start_time=start_dt.time(),
        end_time=end_dt.time(),
        category=ItineraryItemCategory.FREE_TIME,
        title=title,
        description=description,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        cost=ItemCost(
            amount=None,
            currency=currency,
            is_estimate=False,
            data_kind=PriceDataKind.FREE,
        ),
        source="planner",
        source_id=None,
        data_status=PriceDataKind.FREE,
    )
