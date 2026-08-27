# Demo Guide

Manual walkthrough for the **AI Trip Planner** using the verified demo provider stack (`APP_MODE=demo`).

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| Docker | PostgreSQL + pgvector via `infra/docker-compose.yml` |
| Node.js ≥ 20, pnpm 9+ | Monorepo uses pnpm 11.x |
| Python 3.13, uv | API runtime |
| Clerk development instance | Sign-in for `/planner` |
| Provider API keys | See environment section below |

**Never commit** `apps/api/.env` or `apps/web/.env.local`.

## Environment

### Backend — `apps/api/.env`

```bash
cd apps/api
cp .env.example .env
```

Recommended demo settings (also in `.env.example`):

```env
APP_MODE=demo
LLM_PROVIDER=groq
EMBEDDING_PROVIDER=gemini
FLIGHTS_PROVIDER=serpapi
HOTELS_PROVIDER=stayingapi
STAYINGAPI_ENVIRONMENT=sandbox
PLACES_PROVIDER=geoapify
DISTANCE_PROVIDER=openrouteservice
CURRENCY_PROVIDER=frankfurter
```

Required keys (replace placeholders in `.env`):

- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `SERPAPI_API_KEY`
- `STAYINGAPI_API_KEY`
- `GEOAPIFY_API_KEY`
- `OPENROUTESERVICE_API_KEY`
- `CLERK_SECRET_KEY`

Database defaults match Docker Compose (`trip_planner` user/database—not the default `postgres` role):

```env
DATABASE_URL=postgresql+asyncpg://trip_planner:trip_planner@localhost:5432/trip_planner
```

### Frontend — `apps/web/.env.local`

```bash
cd apps/web
cp .env.example .env.local
```

Set:

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_API_URL=http://localhost:8000` (or rely on Next.js proxy to the API)

## Start infrastructure

From the repository root:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Apply migrations:

```bash
cd apps/api
pnpm db:migrate
```

## Start backend

```bash
cd apps/api
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health: `http://127.0.0.1:8000/health`

## Start frontend

From the repository root:

```bash
pnpm --filter @agentic-travel-engine/web dev
```

Or run both API and web:

```bash
pnpm dev
```

Planner UI: `http://localhost:3002/planner`

## Sign in

The planner requires Clerk authentication. Sign in with your development account before submitting a trip.

Playwright E2E tests use an internal auth bypass header—this is **not** available in normal browser use.

## Canonical scenario

Open the planner and enter:

```text
Plan a 5-day trip to Dubai for 2 people under ₹1,50,000 from Mumbai.
```

### What to inspect

While planning runs:

1. Open **View execution** / trace drawer — SSE events, parallel tools, per-tool duration.
2. **Flight** — Trip essentials row (route, party total); popover for carrier, schedule, SerpApi provenance.
3. **Hotel** — Stay name, nights, sandbox StayingAPI provenance in popover.
4. **Ground travel** — Estimated local travel total; popover shows route legs from OpenRouteService (estimation, not booking).
5. **Budget** — Total vs ₹1,50,000 cap; remaining or over-budget state; category bar when expanded.
6. **Itinerary** — Day tabs with themes; activities with live/reference/estimated provenance.
7. **Map** — Day-scoped pins; selects activity on click.

**Budget honesty:** Live SerpApi flights plus StayingAPI sandbox stays may exceed ₹1,50,000. The UI should show the real total and offer recovery suggestions—not force an under-budget display.

## Modification

After the initial plan completes:

```text
Make day 2 more relaxed.
```

Confirm:

- Modification summary (affected day, change facts).
- Day 2 itinerary updates; other days largely preserved.
- Budget recomputed if activity costs changed.
- Trace shows modification path nodes.

Then try:

```text
Make the trip more budget friendly.
```

Confirm budget-oriented suggestions or scope resolution in the UI; exact outcomes depend on catalog and provider data.

## Provider smoke checks

```bash
cd apps/api
uv run python scripts/provider_smoke.py
uv run python scripts/e2e_trip_run.py
```

Flight cache applies on **provider errors** only—not as a silent substitute on successful live searches.

## Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Redirect to sign-in on `/planner` | Not authenticated | Sign in via Clerk |
| No flights / SerpApi errors | Key, quota, or parameter issue | Verify `SERPAPI_API_KEY`; check API logs |
| Hotels show **Sandbox** | Expected | StayingAPI `sandbox` environment |
| Only one hotel candidate | Sandbox inventory limits | Normal for demo; not full market coverage |
| Budget over requested cap | Live flight + stay costs | Expected; use recovery suggestions |
| Hotel excluded from total | Currency conversion unavailable | Check Frankfurter + `source_currency` in budget panel |
| Trace empty | SSE or API connection | Confirm API on :8000, `FRONTEND_ORIGIN` |
| Open-Meteo gaps | Forecast horizon | Weather beyond provider horizon may be unavailable |
| Run lost after API restart | In-memory checkpoints | Start a new planning run |
| Hydration warnings | Stale client bundle | Hard refresh; ensure single Next dev server |

## Security

Rotate any provider key that may have appeared in logs during debugging. The API suppresses credential-bearing URLs in httpx logs where configured.

## Screenshots

Portfolio capture guide: [`screenshots/README.md`](screenshots/README.md) (recommended viewport **1440×900**).
