# AI Trip Planner API

FastAPI backend for the AI Trip Planner monorepo.

## Local development

```bash
uv sync
cp .env.example .env
pnpm db:up
pnpm db:migrate
pnpm dev
```

The API runs at `http://127.0.0.1:8000`.

## Authentication

Authentication uses [Clerk](https://clerk.com) as the initial provider. Clerk-specific verification lives in `app/auth/clerk.py`. Application code depends on the provider-agnostic `CurrentUser` abstraction instead of Clerk SDK types.

### Required Clerk configuration

Set these values in `apps/api/.env`:

| Variable | Purpose |
|----------|---------|
| `CLERK_SECRET_KEY` | Clerk secret key used for server-side token verification |
| `CLERK_JWT_KEY` | Optional PEM public key for networkless JWT verification |
| `CLERK_AUTHORIZED_PARTIES` | Comma-separated frontend origins allowed in the `azp` claim (default: `http://localhost:3002`) |

Never commit real Clerk secrets. Use `.env.example` as the template.

### Authenticated requests

Send a Clerk session token on each protected request:

```http
Authorization: Bearer <clerk-session-token>
```

The API verifies the token server-side, maps the Clerk subject (`sub`) to `users.external_auth_id`, and resolves or creates the local user record.

### Identity endpoint

```http
GET /api/auth/me
```

Returns the authenticated local user. Missing or invalid authentication returns `401 Unauthorized`.

### Ownership semantics

Trip-scoped routes use `get_owned_trip` to ensure `trip.user_id == current_user.id`.

- Missing/invalid authentication → `401`
- Authenticated but trip belongs to another user → `403 Forbidden`
- Authenticated but trip does not exist → `404 Not Found`

A protected ownership probe is available for tests:

```http
GET /api/trips/{trip_id}/ownership
```

## Database

### Start PostgreSQL locally

From `apps/api`:

```bash
pnpm db:up
```

This starts PostgreSQL 18 via `infra/docker-compose.yml`.

### Configure environment

Copy the example file and adjust if needed:

```bash
cp .env.example .env
```

The canonical connection string is `DATABASE_URL`. Component variables (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`) are also supported.

### Apply migrations

```bash
pnpm db:migrate
```

### Create a new migration

```bash
pnpm db:revision "describe change"
```

Review the generated file under `alembic/versions/` before applying it.

### Downgrade

```bash
pnpm db:downgrade
```

### Run database tests

Database tests use an isolated PostgreSQL 18 container via Testcontainers and do not depend on a globally installed PostgreSQL instance.

```bash
pnpm test
```

## Tests

```bash
uv run pytest
```

## Trip planner agent (Phase 2A)

The LangGraph orchestration foundation lives in `app/agent/`. See `app/agent/README.md` for graph topology, state model, routing, and resume behavior.

Invoke the graph through `TripPlannerAgentService` rather than importing node internals directly:

```python
from app.agent import TripPlannerAgentService

service = TripPlannerAgentService()
result = service.start("Plan a 5-day trip to Dubai for 2 people.")
```

## LLM extraction (Phase 2B)

Requirement extraction uses Anthropic Claude through the provider-agnostic `LLMAdapter` interface in `app/llm/`.

### Configuration

Set these values in `apps/api/.env`:

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | LLM provider identifier (default: `anthropic`) |
| `ANTHROPIC_API_KEY` | Server-side Anthropic API key |
| `ANTHROPIC_MODEL` | Model name for structured extraction |
| `LLM_MAX_TOKENS` | Maximum tokens for extraction responses |

Never commit real API keys or expose them to the frontend.

### Extraction responsibilities

The LLM extracts structured `TripRequest` fields from natural-language input only.

It is explicitly prohibited from:

- inventing missing budget, dates, destinations, travelers, or preferences
- calculating authoritative budgets
- calling travel APIs or generating itineraries
- deciding whether requirements are complete

Deterministic validation in `validate_requirements` remains the source of truth for completeness.

## Agent planning API (Phase 2C)

Authenticated endpoints expose the ask_user/resume lifecycle without streaming.

### Start a run

```http
POST /api/agent/runs
Authorization: Bearer <clerk-session-token>
Content-Type: application/json

{
  "message": "Plan a 5-day trip to Dubai for 2 people."
}
```

Returns `201 Created` with a structured response:

| `status` | Meaning |
|----------|---------|
| `complete` | All required fields are present |
| `needs_clarification` | Missing fields are listed in `missing_fields` |
| `failed` | Extraction failed; see `error` |

When clarification is required, `clarification` includes machine-readable prompts. The API does not invent missing budget, dates, or departure city values.

### Submit clarification

```http
POST /api/agent/runs/{run_id}/messages
Authorization: Bearer <clerk-session-token>
Content-Type: application/json

{
  "message": "Budget is ₹1,50,000 and we're departing from Mumbai."
}
```

Resumes the same graph checkpoint, merges new information into the existing `trip_request`, and re-runs validation. Multiple clarification turns are supported until requirements are complete.

When the run already has a valid completed itinerary, the same endpoint routes through selective modification (Phase 6A) instead of restarting full planning.

### Fetch run state (Phase 7A)

```http
GET /api/agent/runs/{run_id}
Authorization: Bearer <clerk-session-token>
```

Returns the latest typed run representation for an owned planning session. Uses the same `AgentRunResponse` contract and conversation mapper as the POST endpoints.

| Status | Meaning |
|--------|---------|
| `401` | Unauthenticated |
| `403` | Run belongs to another user |
| `404` | Unknown run (or expired after API restart) |

Run state is read from the in-process `AgentRunRegistry` / LangGraph checkpoint. This endpoint does not introduce durable Redis or Postgres checkpointing.

### Conversation lifecycle (Phase 6B)

```text
POST /api/agent/runs → initial planning
    ↓
needs_clarification → clarification messages on /runs/{run_id}/messages
    ↓
complete itinerary
    ↓
follow-up /runs/{run_id}/messages → modification (selective refresh → critic)
    ↓
updated itinerary or failed modification with prior plan preserved
```

Responses expose typed `operation.operation_type`:

| Value | When |
| --- | --- |
| `initial_plan` | First message on a new run |
| `clarification` | Follow-up while requirements are incomplete (`awaiting_user`) |
| `modification` | Follow-up when a valid itinerary already exists |

Additional response fields for clients:

- `operation`: affected days, refreshed sources, `budget_changed`, summary
- `itinerary`: approved itinerary only (including preserved plan after failed modification)
- `budget`, `critic`, `tool_availability`: structured summaries
- `planning_failure` / `modification_failure`: safe failure metadata

Raw LangGraph state and exception traces are never returned.

### Ownership and persistence

- Each run is associated with the authenticated application user at creation time.
- Another user cannot resume the same `run_id` (`403 Forbidden`).
- Unknown `run_id` values return `404 Not Found`.
- Run ownership and graph checkpoints are stored in process memory only. Restarting the API clears in-flight runs.
