# Trip Planner Agent (Phase 2A / 3A)

This module contains the production-shaped LangGraph orchestration for the AI Trip Planner.

## Graph topology

```text
START
  ↓
extract_requirements
  ↓
validate_requirements
  ├── complete → fetch_weather → END
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
| `weather_tool_metadata` | Tool-call provenance for observability |
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

## Deferred to later phases

- Additional MCP tools (flights, hotels, restaurants, attractions, maps, currency)
- RAG, budget engine, itinerary generation, critic loop
- SSE streaming endpoints
- Langfuse tracing
- Production checkpoint storage
- Redis-backed weather cache

## Dependencies

- `langgraph==1.2.11`
- `anthropic==1.0.0` (structured extraction via `messages.parse`)
- `mcp>=2.0.0` (weather MCP server in `packages/mcp-tools`)
