"""Builder, scheduling, geography, weather, meal, cost, and provenance tests."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

from app.budget.schemas import PriceDataKind
from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.builder import ItineraryBuilder
from app.itinerary.catalog import build_grounded_catalog
from app.itinerary.clustering import (
    order_attractions_by_proximity,
    select_weather_aware_attractions,
)
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.materializer import materialize_itinerary
from app.itinerary.schemas import CandidateDayPlan, ItinerarySelectionCandidate
from app.itinerary.travel import TravelTimeEstimator
from app.itinerary.validator import validate_candidate, validate_itinerary

from tests.itinerary.fixtures import (
    example_candidate,
    example_itinerary_context,
    fast_assumptions,
)


def test_fake_composer_returns_valid_structured_candidate() -> None:
    context = example_itinerary_context(duration_days=5)
    catalog = build_grounded_catalog(context)
    candidate = FakeItineraryComposer().compose(context=context, catalog=catalog)

    validation = validate_candidate(candidate, context=context, catalog=catalog)
    assert validation.is_valid is True
    assert len(candidate.days) == 5


def test_malformed_candidate_rejected_for_wrong_day_count() -> None:
    context = example_itinerary_context(duration_days=5)
    catalog = build_grounded_catalog(context)
    candidate = ItinerarySelectionCandidate(
        days=[
            CandidateDayPlan(
                day_number=1,
                attraction_source_ids=["places/museum"],
                restaurant_source_id="places/restaurant-a",
            )
        ]
    )

    validation = validate_candidate(candidate, context=context, catalog=catalog)
    assert validation.is_valid is False
    assert any(issue.code == "day_count_mismatch" for issue in validation.issues)


def test_unsupported_source_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    catalog = build_grounded_catalog(context)
    candidate = ItinerarySelectionCandidate(
        days=[
            CandidateDayPlan(
                day_number=1,
                attraction_source_ids=["places/invented"],
                restaurant_source_id="places/restaurant-a",
            )
        ]
    )

    validation = validate_candidate(candidate, context=context, catalog=catalog)
    assert validation.is_valid is False
    assert any(issue.code == "unknown_attraction_source" for issue in validation.issues)


def test_fabricated_restaurant_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    catalog = build_grounded_catalog(context)
    candidate = ItinerarySelectionCandidate(
        days=[
            CandidateDayPlan(
                day_number=1,
                attraction_source_ids=["places/museum"],
                restaurant_source_id="places/fake-restaurant",
            )
        ]
    )

    validation = validate_candidate(candidate, context=context, catalog=catalog)
    assert validation.is_valid is False
    assert any(issue.code == "unknown_restaurant_source" for issue in validation.issues)


def test_builder_produces_validated_itinerary() -> None:
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(example_itinerary_context(duration_days=5))

    assert result.success is True
    assert result.itinerary is not None
    assert len(result.itinerary.days) == 5
    assert result.validation.is_valid is True


def test_exact_day_count_enforced() -> None:
    context = example_itinerary_context(duration_days=5)
    catalog = build_grounded_catalog(context)
    candidate = example_candidate(duration_days=5)
    itinerary = materialize_itinerary(
        candidate,
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
    )

    validation = validate_itinerary(itinerary, context=context, catalog=catalog)
    assert validation.is_valid is True
    assert len(itinerary.days) == 5


def test_at_least_one_meal_per_day() -> None:
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(example_itinerary_context(duration_days=3))

    assert result.itinerary is not None
    for day in result.itinerary.days:
        assert day.meal is not None
        assert day.meal.item.category.value == "restaurant"
        assert day.meal.item.source_id in {
            "places/restaurant-a",
            "places/restaurant-b",
            "places/restaurant-c",
            "places/restaurant-d",
            "places/restaurant-e",
        }


def test_no_invented_restaurants_in_materialized_items() -> None:
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(example_itinerary_context(duration_days=2))
    assert result.itinerary is not None

    restaurant_ids = {
        "places/restaurant-a",
        "places/restaurant-b",
        "places/restaurant-c",
        "places/restaurant-d",
        "places/restaurant-e",
    }
    for day in result.itinerary.days:
        meal_ids = [
            item.source_id for item in day.items if item.category.value == "restaurant"
        ]
        assert all(source_id in restaurant_ids for source_id in meal_ids)


def test_daily_subtotal_matches_items() -> None:
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(example_itinerary_context(duration_days=2))
    assert result.itinerary is not None

    for day in result.itinerary.days:
        computed = Decimal("0")
        for item in day.items:
            if (
                item.cost.amount is not None
                and item.cost.data_kind != PriceDataKind.UNAVAILABLE
            ):
                computed += item.cost.amount
        assert day.subtotal == computed


def test_budget_relationship_preserved() -> None:
    context = example_itinerary_context(duration_days=2)
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(context)

    assert result.itinerary is not None
    assert result.itinerary.budget_amount == context.budget_result.budget_amount
    assert result.itinerary.budget_total_cost == context.budget_result.total_cost
    assert result.itinerary.budget_remaining == context.budget_result.remaining


def test_item_costs_use_estimate_semantics() -> None:
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(example_itinerary_context(duration_days=1))
    assert result.itinerary is not None

    attraction = next(
        item
        for item in result.itinerary.days[0].items
        if item.category.value == "attraction"
    )
    assert attraction.cost.is_estimate is True
    assert attraction.cost.data_kind == PriceDataKind.ESTIMATED


def test_flight_and_hotel_infrastructure_items_present() -> None:
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(example_itinerary_context(duration_days=2))
    assert result.itinerary is not None

    categories = {item.category.value for item in result.itinerary.infrastructure_items}
    assert "flight" in categories
    assert "hotel" in categories
    flight = next(
        item
        for item in result.itinerary.infrastructure_items
        if item.category.value == "flight"
    )
    assert "→" in flight.title
    assert flight.description is not None
    assert "Outbound flight" in flight.description


def test_nearby_attractions_grouped_by_proximity() -> None:
    context = example_itinerary_context(duration_days=1)
    catalog = build_grounded_catalog(context)
    estimator = TravelTimeEstimator(context.distance_matrix, fast_assumptions())
    ordered = order_attractions_by_proximity(
        ["places/museum", "places/park", "places/mall"],
        catalog,
        estimator,
    )

    assert ordered[0] == "places/museum"
    assert ordered[-1] in {"places/mall", "places/park"}


def test_distance_matrix_data_used_for_travel_legs() -> None:
    context = example_itinerary_context(duration_days=1)
    catalog = build_grounded_catalog(context)
    candidate = ItinerarySelectionCandidate(
        days=[
            CandidateDayPlan(
                day_number=1,
                attraction_source_ids=["places/museum", "places/park"],
                restaurant_source_id="places/restaurant-a",
            )
        ]
    )
    itinerary = materialize_itinerary(
        candidate,
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
    )

    assert itinerary.days[0].travel_legs
    assert itinerary.days[0].travel_legs[0].source == "google_distance_matrix"
    assert itinerary.days[0].travel_legs[0].duration_seconds == 900


def test_unavailable_distance_data_falls_back_safely() -> None:
    estimator = TravelTimeEstimator(None, fast_assumptions())
    estimate = estimator.estimate(
        origin_lat=25.2632,
        origin_lng=55.2972,
        destination_lat=25.2285,
        destination_lng=55.3073,
    )

    assert estimate.source == "deterministic_haversine"
    assert estimate.data_status == PriceDataKind.ESTIMATED
    assert estimate.duration_seconds >= 60


def test_rainy_day_prefers_indoor_attractions() -> None:
    context = example_itinerary_context(duration_days=1, rainy_day=1)
    catalog = build_grounded_catalog(context)
    selected = select_weather_aware_attractions(
        catalog.attraction_ids(),
        day_number=1,
        catalog=catalog,
        assumptions=SchedulingAssumptions(),
        max_items=2,
    )

    assert selected[0] in {"places/museum", "places/mall"}


def test_normal_weather_keeps_outdoor_options() -> None:
    context = example_itinerary_context(duration_days=1, rainy_day=None)
    catalog = build_grounded_catalog(context)
    selected = select_weather_aware_attractions(
        catalog.attraction_ids(),
        day_number=1,
        catalog=catalog,
        assumptions=SchedulingAssumptions(),
        max_items=2,
    )

    assert "places/park" in selected


def test_overlapping_schedule_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    catalog = build_grounded_catalog(context)
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    result = builder.build_from_context(context)
    assert result.itinerary is not None

    broken = result.itinerary.model_copy(deep=True)
    broken.days[0].items[0] = (
        broken.days[0]
        .items[0]
        .model_copy(update={"start_time": time(9, 0), "end_time": time(18, 0)})
    )
    validation = validate_itinerary(broken, context=context, catalog=catalog)
    assert validation.is_valid is False
    assert any(issue.code == "time_overlap" for issue in validation.issues)


def test_deterministic_validation_is_stable() -> None:
    context = example_itinerary_context(duration_days=3)
    catalog = build_grounded_catalog(context)
    candidate = example_candidate(duration_days=3)
    itinerary = materialize_itinerary(
        candidate,
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
    )

    first = validate_itinerary(itinerary, context=context, catalog=catalog)
    second = validate_itinerary(itinerary, context=context, catalog=catalog)
    assert first == second


def test_invalid_builder_candidate_is_not_persisted_as_success() -> None:
    class RejectComposer(FakeItineraryComposer):
        def compose(
            self,
            *,
            context: object,
            catalog: object,
        ) -> ItinerarySelectionCandidate:
            return ItinerarySelectionCandidate(
                days=[
                    CandidateDayPlan(
                        day_number=1,
                        attraction_source_ids=["places/invented"],
                        restaurant_source_id="places/restaurant-a",
                    )
                ]
            )

    builder = ItineraryBuilder(composer=RejectComposer())
    result = builder.build_from_context(example_itinerary_context(duration_days=5))

    assert result.success is False
    assert result.itinerary is None
    assert result.validation.is_valid is False


def test_implausible_travel_duration_does_not_create_invalid_leg() -> None:
    from datetime import date, datetime

    from app.itinerary.materializer import _build_travel_leg
    from app.itinerary.schemas import ItemCost, ItineraryItem, ItineraryItemCategory
    from app.itinerary.travel import TravelEstimate

    class HugeTravel(TravelTimeEstimator):
        def estimate(
            self,
            *,
            origin_lat: float,
            origin_lng: float,
            destination_lat: float,
            destination_lng: float,
        ) -> TravelEstimate:
            return TravelEstimate(
                distance_meters=1_000_000,
                duration_seconds=50_000,
                travel_mode="driving",
                source="test",
                data_status=PriceDataKind.LIVE,
            )

    previous = ItineraryItem(
        item_id="slow-morning",
        day_number=2,
        start_time=time(10, 0),
        end_time=time(10, 45),
        category=ItineraryItemCategory.FREE_TIME,
        title="Slow morning",
        latitude=25.2,
        longitude=55.2,
        cost=ItemCost(amount=None, currency="INR", data_kind=PriceDataKind.FREE),
        source="planner",
        source_id=None,
        data_status=PriceDataKind.FREE,
    )
    started = datetime.combine(date.today(), time(10, 45))
    leg, cursor = _build_travel_leg(
        previous_item=previous,
        next_lat=25.3,
        next_lng=55.3,
        day_number=2,
        cursor=started,
        estimator=HugeTravel(None),
        assumptions=SchedulingAssumptions(),
        leg_index=0,
        travel_buffer_minutes=20,
    )
    assert leg is None
    assert cursor > started
