from app.db.models import (
    AgentTrace,
    Budget,
    ItineraryDay,
    ItineraryItem,
    Message,
    ToolResult,
    Trip,
    TripPreference,
    User,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


async def test_database_connectivity(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


async def test_user_trip_relationship_persists(db_session: AsyncSession) -> None:
    user = User(email="traveler@example.com", display_name="Traveler")
    trip = Trip(user=user, title="Tokyo Spring", destination="Tokyo", status="draft")
    db_session.add(user)
    await db_session.commit()

    loaded = await db_session.get(Trip, trip.id)
    assert loaded is not None
    assert loaded.user_id == user.id
    assert loaded.destination == "Tokyo"


async def test_trip_related_entities_persist(db_session: AsyncSession) -> None:
    user = User(email="planner@example.com")
    trip = Trip(user=user, title="Paris Week", destination="Paris")
    TripPreference(
        trip=trip,
        preference_key="pace",
        preference_value={"value": "relaxed"},
    )
    Message(trip=trip, role="user", content="Plan a relaxed week in Paris.")
    ToolResult(
        trip=trip,
        tool_name="weather_lookup",
        request_payload={"city": "Paris"},
        response_payload={"summary": "Mild"},
        status="completed",
    )
    itinerary_day = ItineraryDay(trip=trip, day_index=1, summary="Arrival day")
    ItineraryItem(
        itinerary_day=itinerary_day,
        sort_order=1,
        item_type="activity",
        title="Check in",
    )
    Budget(
        trip=trip,
        budget_category="total",
        amount_minor=250_000,
        currency_code="EUR",
        label="Trip total",
    )
    AgentTrace(
        trip=trip,
        trace_name="requirements_validation",
        input_payload={"destination": "Paris"},
        output_payload={"valid": True},
        status="completed",
    )

    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(
        select(Trip)
        .where(Trip.id == trip.id)
        .options(
            selectinload(Trip.preferences),
            selectinload(Trip.messages),
            selectinload(Trip.tool_results),
            selectinload(Trip.itinerary_days).selectinload(ItineraryDay.items),
            selectinload(Trip.budgets),
            selectinload(Trip.agent_traces),
        )
    )
    loaded_trip = result.scalar_one()

    assert len(loaded_trip.preferences) == 1
    assert loaded_trip.preferences[0].preference_key == "pace"
    assert len(loaded_trip.messages) == 1
    assert loaded_trip.messages[0].role == "user"
    assert len(loaded_trip.tool_results) == 1
    assert loaded_trip.tool_results[0].tool_name == "weather_lookup"
    assert len(loaded_trip.itinerary_days) == 1
    assert len(loaded_trip.itinerary_days[0].items) == 1
    assert loaded_trip.itinerary_days[0].items[0].title == "Check in"
    assert len(loaded_trip.budgets) == 1
    assert loaded_trip.budgets[0].amount_minor == 250_000
    assert len(loaded_trip.agent_traces) == 1
    assert loaded_trip.agent_traces[0].trace_name == "requirements_validation"


async def test_foreign_key_relationship_is_enforced(db_session: AsyncSession) -> None:
    user = User(email="fk-test@example.com")
    trip = Trip(user=user, title="Constraint test")
    db_session.add(user)
    await db_session.commit()

    child_trip_id = trip.id
    await db_session.delete(user)
    await db_session.commit()

    orphaned_trip = await db_session.get(Trip, child_trip_id)
    assert orphaned_trip is None
