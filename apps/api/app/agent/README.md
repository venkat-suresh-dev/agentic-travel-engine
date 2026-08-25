# Trip Planner Agent (Phase 2A / 3A / 3B / 3C / 3D / 3E / 3F / 3G / 4 / 5A)

This module contains the production-shaped LangGraph orchestration for the AI Trip Planner.

## Graph topology

```text
START
  ↓
extract_requirements
  ↓
validate_requirements
  ├── incomplete → ask_user → END
  └── complete → retrieve_context (optional RAG; no-op without retriever)
         ↓
     parallel independent tool fan-out
         ├── fetch_weather
         ├── search_flights
         ├── search_hotels
         ├── get_distance_matrix
         ├── search_restaurants
         └── search_attractions
         ↓
     aggregate_independent_tools
         ↓
     convert_currency   (depends on flight_search)
         ↓
     compute_budget     (deterministic; authoritative totals)
         ↓
     finalize_run
         ↓
        END
```

## Parallel orchestration (Phase 3G)

After validation reports complete requirements, an optional `retrieve_context` node may fetch curated destination reference data (Phase 4 RAG). When no `RAGRetriever` is injected, the node is a no-op and does not block tool fan-out.

Six independent travel-data tools then fan out concurrently via LangGraph `Send` packets. Each tool writes only to its own typed state fields. A barrier node (`aggregate_independent_tools`) waits for all parallel branches before dependency-aware currency conversion runs.

**Concurrency limit:** `AGENT_TOOL_CONCURRENCY_LIMIT` (default `4`) bounds simultaneous tool executions through a shared `ToolConcurrencyLimiter` semaphore. This protects external providers from unbounded bursts without replacing each tool's own timeout/retry/cache behavior.

**Currency dependency:** `convert_currency` runs after the parallel fan-out because it requires the lowest flight offer from `flight_search`. It is not forced into the concurrent batch.

**Distance dependency:** `get_distance_matrix` runs in parallel because it only needs validated `departure_city` and `destination` from `trip_request` (resolved via `LocationResolver`).

### Aggregate run status

| Status | Meaning |
| --- | --- |
| `success` | All executed tools returned live/cached results |
| `partial` | One or more tools unavailable, but at least one succeeded |
| `failed` | All independent tools failed; no usable tool facts |

The public API contract (`complete` / `needs_clarification` / `failed`) is unchanged. Tool-level partial availability is represented inside the completed result via `aggregate_run_status` and per-tool `data_status` fields.

### Failure isolation

A single provider failure does not fail the entire run. Unavailable tool results are preserved alongside successful results. Unexpected tool exceptions are caught at the node boundary and recorded in `tool_orchestration` without aborting sibling branches.

### Orchestration metadata

`tool_orchestration` (per-tool records merged via reducer) and `tool_orchestration_summary` capture:

- `tool_name`, `provider`, `started_at`, `completed_at`, `duration_ms`, `status`
- run-level `aggregate_run_status` and `run_id` (injected at the service boundary)

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
| `currency_conversion` | Normalized reference-rate conversion from the MCP currency tool |
| `currency_tool_metadata` | Tool-call provenance for currency conversion |
| `tool_orchestration` | Per-tool execution records (reducer-merged) |
| `aggregate_run_status` | `success` / `partial` / `failed` aggregate outcome |
| `tool_orchestration_summary` | Run-level orchestration summary |
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

### Parallel independent tools (Phase 3G)

The following nodes run concurrently after validation when requirements are complete:

- `fetch_weather` — Open-Meteo forecast via `WeatherTool`
- `search_flights` — Amadeus flight offers via `FlightTool`
- `search_hotels` — Amadeus hotel search via `HotelTool`
- `get_distance_matrix` — OpenRouteService matrix via `DistanceTool`
- `search_restaurants` — Google Places via `RestaurantTool`
- `search_attractions` — Google Places via `AttractionTool`

Each node uses `run_bounded_tool_node` for concurrency limiting and orchestration tracing. Per-tool timeout/retry/cache/degraded-mode behavior remains inside each MCP service.

### `aggregate_independent_tools` (Phase 3G)

- Barrier node after all parallel branches complete.
- Computes interim `aggregate_run_status` from independent tool outcomes.
- Does **not** merge tool metadata across tools.

### `convert_currency` (Phase 3F / dependency-aware in 3G)

- Invoked only after independent tools aggregate.
- Builds a deterministic conversion plan from the lowest-priced flight offer and `trip_request.budget_currency`.
- Calls `CurrencyTool` → `CurrencyService` → Frankfurter v2 reference rates via the MCP tool package.
- Stores converted representation and tool metadata separately; original flight offer prices remain unchanged.
- Skips provider access for same-currency conversion (`rate = 1`, `source = deterministic`).
- Does **not** let the LLM invent exchange rates or perform authoritative accounting.

### `finalize_run` (Phase 3G)

- Sets final `aggregate_run_status` including currency outcome.
- Builds `tool_orchestration_summary` with deterministic tool record ordering.
- Sets `status = complete`.

### `ask_user`

- Produces structured clarification metadata for missing fields.
- Does **not** act as a conversational agent.

## Routing

`app/agent/routing.py` contains `route_after_validation`, which routes:

- complete requirements → parallel fan-out via `Send` packets
- incomplete requirements → `ask_user`

No external tool runs before requirements are deterministically validated as complete.

## Tool boundary

Application tools in `app/tools/` wrap MCP package services. The graph never calls MCP servers directly.

```text
LangGraph node
    ↓
app/tools/*Tool
    ↓
mcp_tools/*/service
    ↓
provider
```

## Dependencies

- `langgraph==1.2.11`

## Conversation API lifecycle (Phase 6B)

The authenticated agent API exposes the full planning conversation through two endpoints:

```text
POST /api/agent/runs
POST /api/agent/runs/{run_id}/messages
```

### Lifecycle

```text
initial request
    ↓
clarification if incomplete (needs_clarification)
    ↓
completed plan (complete)
    ↓
follow-up modification message
    ↓
selective refresh (when required)
    ↓
critic
    ↓
updated plan (complete) or failed modification (failed, prior plan preserved)
```

### Clarification vs modification

Classification uses persisted run state, not natural-language heuristics alone:

| Run state | Follow-up message routes to |
| --- | --- |
| `awaiting_user` / incomplete validation | **clarification** (`extract_requirements`) |
| `planning_failed` without valid itinerary | **clarification** (safest resume path) |
| Valid approved `itinerary`, `planning_failed = false` | **modification** (`extract_modification`) |

The API exposes `operation.operation_type` as `initial_plan`, `clarification`, or `modification`.

### Response contract

`AgentRunResponse` includes typed fields for Phase 7 consumers:

- `status`: `complete` / `needs_clarification` / `failed`
- `operation`: structured `OperationResult` (affected days, refreshed sources, budget flag)
- `itinerary`: only when a valid approved itinerary exists
- `budget`, `critic`, `tool_availability`: summaries when available
- `planning_failure` / `modification_failure`: structured failure metadata
- `error`: safe user-facing message (no exception traces)

Raw LangGraph state is never returned.

### Failure safety

Failed modifications restore `previous_itinerary` internally and return `status = failed` with `modification_failure.preserved_itinerary = true`. The client still receives the last valid itinerary.

### Persistence limitation

`AgentRunRegistry` and LangGraph `InMemorySaver` are **process-local**. Run checkpoints and ownership mappings do not survive API process restarts. Durable checkpointing is out of scope for Phase 6B.
