"""Run one genuine local trip-planning graph execution."""

from __future__ import annotations

import logging
import sys

from app.api.deps import get_trip_planner_agent_service

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> int:
    message = (
        "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000 from Mumbai."
    )
    service = get_trip_planner_agent_service()
    result = service.start(message)

    print(f"status={result.status.value}")
    print(f"aggregate_run_status={result.aggregate_run_status}")
    print(f"planning_failed={result.planning_failed}")
    if result.trip_request:
        print(
            "trip_request:",
            result.trip_request.destination,
            result.trip_request.departure_city,
            result.trip_request.travelers,
            result.trip_request.budget_amount,
            result.trip_request.budget_currency,
        )
    if result.flight_search:
        print(
            "flights:",
            result.flight_search.data_status,
            len(result.flight_search.offers),
            result.flight_search.source,
        )
    if result.hotel_search:
        print(
            "hotels:",
            result.hotel_search.data_status,
            len(result.hotel_search.hotels),
            result.hotel_search.source,
        )
    if result.weather_forecast:
        print("weather_days:", len(result.weather_forecast.forecast))
    if result.restaurant_search:
        print("restaurants:", len(result.restaurant_search.restaurants))
    if result.attraction_search:
        print("attractions:", len(result.attraction_search.attractions))
    if result.budget_result:
        print("budget_total:", result.budget_result.total_cost)
    if result.itinerary_build_result:
        print(
            "itinerary_days:",
            len(result.itinerary_build_result.itinerary.days),
        )
    if result.critic_result:
        print("critic_passed:", result.critic_result.passed)
    if result.tool_orchestration_summary:
        print("tool_summary_status:", result.tool_orchestration_summary.aggregate_status)

    ok = (
        result.itinerary_build_result is not None
        and len(result.itinerary_build_result.itinerary.days) > 0
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
