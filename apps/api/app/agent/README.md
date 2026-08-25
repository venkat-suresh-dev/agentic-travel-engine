# Trip Planner Agent (Phase 2A / 3A / 3B / 3C / 3D / 3E)

This module contains the production-shaped LangGraph orchestration for the AI Trip Planner.

## Graph topology

```text
START
  ↓
extract_requirements
  ↓
validate_requirements
  ├── complete → fetch_weather → search_flights → search_hotels → get_distance_matrix → search_restaurants → search_attractions → END
  └── incomplete → ask_user → END
```

## State model

Graph state lives in `app/agent/state.py` as `AgentState` and is intentionally separate from SQLAlchemy ORM models.

Important fields:

| Field | Responsibility |
| --- | --- |
| `user_request` | Raw initial planning request |
| `user_clarification` | Follow-up user text used when resuming an interrupted graph |
| `messages` | Conversation history captured by nodes |
| `trip_request` | Structured requirements produced by extraction |
| `validation` | Deterministic completeness result |
| `clarification` | Structured prompts for missing fields |
| `weather_forecast` | Normalized weather facts from the MCP weather tool |
| `weather_tool_metadata` | Tool-call provenance for weather |
| `flight_search` | Normalized flight offers from the MCP flight tool |
| `flight_tool_metadata` | Tool-call provenance for flights |
| `hotel_search` | Normalized hotel offers from the MCP hotel tool |
| `hotel_tool_metadata` | Tool-call provenance for hotels |
| `distance_matrix` | Normalized distance/duration facts from the MCP distance tool |
| `distance_tool_metadata` | Tool-call provenance for distance |
| `restaurant_search` | Normalized restaurant results from the MCP places tool |
| `restaurant_tool_metadata` | Tool-call provenance for restaurants |
| `attraction_search` | Normalized attraction results from the MCP places tool |
| `attraction_tool_metadata` | Tool-call provenance for attractions |
| `status` | Current graph lifecycle status |

Structured domain models live in `app/domain/trip_request.py`.

## Node responsibilities

### `extract_requirements`

- Converts free-form user text into structured `TripRequest` state through the
  provider-agnostic `LLMAdapter` boundary.
- Uses Anthropic structured output in production via `app/llm/anthropic.py`.
- Merges clarification text into any previously extracted requirements.
- Does **not** perform validation, routing, or external travel API calls.

### `validate_requirements`

- Deterministically checks whether required fields are present.
- Required fields: destination, travelers, budget, departure city, and either duration or start date.
- Does **not** invent missing values.

### `fetch_weather` (Phase 3A)

- Invoked only after validation reports complete requirements.
- Builds a deterministic `WeatherForecastRequest` from the validated `TripRequest`.
- Calls `WeatherTool` → `WeatherService` → Open-Meteo via the MCP tool package.
- Stores normalized forecast data and tool metadata in graph state.
- Does **not** let the LLM invent weather facts.

### `search_flights` (Phase 3B)

- Invoked only after weather fetch on the complete-request path.
- Builds a deterministic `FlightSearchRequest` from validated `TripRequest` fields.
- Resolves departure city and destination to IATA codes via `AirportCodeResolver`.
- Calls `FlightTool` → `FlightService` → Amadeus Flight Offers Search.
- Stores normalized offers and tool metadata in graph state.
- Results are search snapshots only — not booking guarantees.
- Does **not** let the LLM invent flight prices or schedules.

### `search_hotels` (Phase 3C)

- Invoked only after flight search on the complete-request path.
- Builds a deterministic `HotelSearchRequest` from validated `TripRequest` fields.
- Resolves destination to an IATA city code via `CityCodeResolver`.
- Calls `HotelTool` → `HotelService` → Amadeus Hotel List + Hotel Search.
- Stores normalized hotel offers and tool metadata in graph state.
- Results are search snapshots only — not booking or availability guarantees.
See `packages/mcp-tools/README.md` for MCP contract, cache, retry, and no-booking semantics.

### `get_distance_matrix` (Phase 3D)

- Invoked only after hotel search on the complete-request path.
- Builds a deterministic `DistanceMatrixRequest` from validated `departure_city` and `destination`.
- Resolves both locations to coordinates via `LocationResolver` (Open-Meteo geocoding).
- Calls `DistanceTool` → `DistanceService` → OpenRouteService Matrix API.
- Stores normalized route facts (`distance_meters`, `duration_seconds`) and tool metadata in graph state.
- Currently supplies a 1×1 departure→destination matrix only; no invented stops or attractions.
- Does **not** let the LLM invent travel times or distances.

### `search_restaurants` (Phase 3E)

- Invoked only after distance lookup on the complete-request path.
- Builds a deterministic `RestaurantSearchRequest` from the validated destination.
- Resolves destination coordinates via `LocationResolver` (Open-Meteo geocoding).
- Calls `RestaurantTool` → `PlacesService` → Google Places Text Search (New).
- Stores normalized restaurant facts and tool metadata in graph state.
- Does **not** let the LLM invent ratings, prices, or hours.

### `search_attractions` (Phase 3E)

- Invoked only after restaurant search on the complete-request path.
- Builds a deterministic `AttractionSearchRequest` from the validated destination.
- Resolves destination coordinates via `LocationResolver`.
- Calls `AttractionTool` → `PlacesService` → Google Places Nearby Search (New).
- Stores normalized attraction facts and tool metadata in graph state.
- Does **not** let the LLM invent venues, ratings, or hours.

### `ask_user`

- Produces structured clarification metadata for missing fields.
- Does **not** act as a conversational agent.

## Routing

`app/agent/routing.py` contains `route_after_validation`, which routes:

- complete requirements → `fetch_weather`
- incomplete requirements → `ask_user`

Routing is tested independently from node implementations.

## Resume behavior

The graph is compiled with LangGraph's `InMemorySaver` checkpointer for thread-scoped state.

1. An incomplete request ends in `awaiting_user` with structured clarification metadata.
2. A later invocation with the same `thread_id` and new `user_clarification` resumes from the checkpoint.
3. `extract_requirements` merges the clarification into the existing `trip_request` without discarding prior values. Merge semantics are implemented in `app/agent/trip_request_merge.py` and preserve existing non-null fields unless the new extraction explicitly supplies a replacement value.

`TripPlannerAgentService` in `app/agent/service.py` exposes:

- `start(user_request, thread_id=...)`
- `resume(thread_id, user_clarification)`
- `get_state(thread_id)`

Production persistence should move to a durable checkpointer (for example Postgres) in a later phase. Redis is intentionally not introduced here.

## API exposure (Phase 2C)

Authenticated HTTP endpoints in `app/api/routes/agent.py` expose the ask_user/resume lifecycle:

- `POST /api/agent/runs` — start a planning run
- `POST /api/agent/runs/{run_id}/messages` — submit clarification and resume

`AgentRunService` in `app/services/agent_runs.py` maps graph results to API-safe responses and enforces per-user run ownership through an in-memory `AgentRunRegistry`. Run IDs correspond to LangGraph `thread_id` values.

Current limitations:

- Run ownership and graph checkpoints are stored in process memory only.
- Restarting the API process clears all in-flight runs.
- Extraction failures return `status: "failed"` in the response body (`201` for new runs, `200` for clarifications) rather than leaking internal errors.
- Durable conversation persistence belongs to a later phase.

## Weather tool boundary (Phase 3A)

```text
fetch_weather node
    ↓
WeatherTool (apps/api)
    ↓
WeatherService (packages/mcp-tools)
    ↓
MCP get_weather_forecast
    ↓
Open-Meteo geocoding + forecast
```

See `packages/mcp-tools/README.md` for MCP contract, cache, retry, and degraded-mode behavior.

## Flight tool boundary (Phase 3B)

```text
search_flights node
    ↓
FlightTool (apps/api)
    ↓
FlightService (packages/mcp-tools)
    ↓
MCP search_flights
    ↓
Amadeus auth + Flight Offers Search
```

See `packages/mcp-tools/README.md` for MCP contract, cache, retry, and no-booking semantics.

## Hotel tool boundary (Phase 3C)

```text
search_hotels node
    ↓
HotelTool (apps/api)
    ↓
HotelService (packages/mcp-tools)
    ↓
MCP search_hotels
    ↓
Amadeus auth + Hotel List + Hotel Search
```

See `packages/mcp-tools/README.md` for MCP contract, cache, retry, and no-booking semantics.

## Distance tool boundary (Phase 3D)

```text
get_distance_matrix node
    ↓
DistanceTool (apps/api)
    ↓
DistanceService (packages/mcp-tools)
    ↓
MCP get_distance_matrix
    ↓
OpenRouteService Matrix API + Open-Meteo geocoding
```

See `packages/mcp-tools/README.md` for MCP contract, cache, retry, and normalized units.

## Places tool boundary (Phase 3E)

```text
search_restaurants / search_attractions nodes
    ↓
RestaurantTool / AttractionTool (apps/api)
    ↓
PlacesService (packages/mcp-tools)
    ↓
MCP search_restaurants / search_attractions
    ↓
Google Places API (New) + Open-Meteo geocoding
```

See `packages/mcp-tools/README.md` for field masks, cache, retry, and no-booking semantics.

## Deferred to later phases

- Additional MCP tools (currency conversion)
- RAG, budget engine, itinerary generation, critic loop
- SSE streaming endpoints
- Langfuse tracing
- Production checkpoint storage
- Redis-backed weather cache

## Dependencies

- `langgraph==1.2.11`
- `anthropic==1.0.0` (structured extraction via `messages.parse`)
- `mcp>=2.0.0` (weather MCP server in `packages/mcp-tools`)
