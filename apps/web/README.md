# AI Trip Planner Web

Next.js App Router frontend for the AI Trip Planner workspace.

## Development

```bash
cp .env.example .env.local
pnpm install
pnpm dev
```

Runs at `http://127.0.0.1:3002`.

For E2E/browser QA without Clerk keys:

```bash
NEXT_PUBLIC_PLAYWRIGHT=1 pnpm dev
```

### Required environment

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | FastAPI backend (`http://127.0.0.1:8000`). In the browser, requests default to same-origin via the Next.js rewrite when unset. |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk publishable key |
| `CLERK_SECRET_KEY` | Clerk secret key for middleware |

## Planner routes

| Route | Purpose |
| --- | --- |
| `/planner` | Premium empty state + initial planning |
| `/planner/[runId]` | Conversation workspace, itinerary, budget, modifications |
| `/sign-in` | Clerk sign-in (theme-aligned) |
| `/sign-up` | Clerk sign-up (theme-aligned) |

## Hydration

`/planner/[runId]` hydrates from `GET /api/agent/runs/{run_id}` via TanStack Query. The server is the source of truth for run state; `sessionStorage` caches conversation history and provides short-lived placeholder data during refresh.

Runs are process-local on the API. A hard refresh works while the backend process still holds the run; after an API restart, expired runs return 404.

## Architecture

```text
Planner UI
  ↓ typed API client (lib/api)
  ↓ TanStack Query (lib/planner/hooks)
  ↓ GET /api/agent/runs/{run_id} + POST mutations
  ↓ sessionStorage (conversation history cache only)
  ↓ FastAPI /api/agent/runs
```

Shared API contracts live in `packages/shared-types`.

## Tests

```bash
pnpm test          # Vitest + RTL
pnpm test:e2e      # Playwright (mocked API)
pnpm type-check
pnpm lint
pnpm build
```
