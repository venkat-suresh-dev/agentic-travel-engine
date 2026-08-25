# Trip Planner Agent (Phase 2A)

This module contains the first production-shaped LangGraph orchestration for the AI Trip Planner.

## Graph topology

```text
START
  ↓
extract_requirements
  ↓
validate_requirements
  ├── complete → END
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

### `ask_user`

- Produces structured clarification metadata for missing fields.
- Does **not** act as a conversational agent.

## Routing

`app/agent/routing.py` contains `route_after_validation`, which routes:

- complete requirements → graph end
- incomplete requirements → `ask_user`

Routing is tested independently from node implementations.

## Resume behavior

The graph is compiled with LangGraph's `InMemorySaver` checkpointer for thread-scoped state.

1. An incomplete request ends in `awaiting_user` with structured clarification metadata.
2. A later invocation with the same `thread_id` and new `user_clarification` resumes from the checkpoint.
3. `extract_requirements` merges the clarification into the existing `trip_request` without discarding prior values.

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
- Durable conversation persistence belongs to a later phase.

## Deferred to later phases

- MCP tools and external travel APIs
- RAG, budget engine, itinerary generation, critic loop
- SSE streaming endpoints
- Langfuse tracing
- Production checkpoint storage

## Dependencies

- `langgraph==1.2.11`
- `anthropic==1.0.0` (structured extraction via `messages.parse`)
