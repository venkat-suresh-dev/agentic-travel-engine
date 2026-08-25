# Phase 5B Itinerary Builder

The itinerary subsystem turns grounded provider facts, RAG reference context, and the authoritative `BudgetResult` into a validated day-by-day itinerary.

## Architecture

```text
ItineraryBuildContext (typed grounded inputs)
        ↓
GroundedCatalog
        ↓
ItineraryComposer (LLM selects grounded source IDs)
        ↓
ItinerarySelectionCandidate
        ↓
validate_candidate()
        ↓
materialize_itinerary() (times, travel legs, costs, subtotals)
        ↓
validate_itinerary()
        ↓
ItineraryBuildResult
```

## Responsibilities

### Composition (`ItineraryComposer`)

- Chooses which grounded attractions and restaurants appear on each day.
- Outputs only structured source ID references.
- Must not invent venues, prices, travel times, or availability.

### Materialization (`materializer.py`)

- Assigns start/end times using `SchedulingAssumptions`.
- Inserts explicit `TravelLeg` intervals from distance-tool data (with documented haversine fallback).
- Adds one meal suggestion per day from restaurant provider results.
- Adds trip-level flight and hotel check-in/check-out infrastructure items.
- Computes daily subtotals and itinerary totals deterministically.

### Validation (`validator.py`)

Independent checks:

- exact `duration_days`
- grounded source IDs only
- one meal per day
- valid time ranges
- no overlaps
- travel buffer ordering
- daily subtotal arithmetic
- unavailable costs are not represented as priced amounts

## Scheduling Assumptions

All default durations, buffers, rainy-day threshold, and estimated activity/meal costs live in `SchedulingAssumptions`.

## Geographic Clustering

`order_attractions_by_proximity()` uses a nearest-neighbor heuristic over travel duration (distance matrix when available) to reduce backtracking within a day.

## Weather Policy

`select_weather_aware_attractions()` reads precipitation probability from weather tool facts. When a day exceeds `rainy_day_precipitation_threshold`, indoor attraction types are preferred first.

## Budget Interaction

`BudgetResult` values are copied onto the itinerary for reference. Item-level itinerary costs for attractions/meals use explicit estimates from assumptions unless provider live prices exist (flights/hotels).

## Source / Provenance Rules

- Attractions and restaurants must reference Google place IDs from tool results.
- Flights reference Amadeus offer IDs.
- Hotels reference provider hotel IDs.
- Travel legs reference distance-tool routes when coordinate pairs match.

## Phase 5B Limitations

- No critic/retry loop (Phase 5C).
- No advanced route optimization beyond nearest-neighbor ordering.
- LLM production path depends on `LLMItineraryComposer`; offline tests use `FakeItineraryComposer`.
- Attraction/meal item costs are estimated unless provider prices are available.

## Phase 5C Handoff

Phase 5C will add a critic that inspects validation failures and retries composition with structured feedback. The validator and schemas in this phase are intended to be reused unchanged.
