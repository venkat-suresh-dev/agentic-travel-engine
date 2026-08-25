# AI Trip Planner v3.0

Foundation monorepo for the AI Trip Planner — a Turborepo workspace with a Next.js frontend, FastAPI backend, and shared TypeScript packages.

## Requirements

| Tool | Version |
|------|---------|
| Node.js | >= 20 (see `.nvmrc`) |
| pnpm | 9+ |
| Python | 3.13 |
| uv | latest stable |

## Install tooling

### pnpm

```bash
corepack enable
corepack prepare pnpm@11.21.0 --activate
```

Or install from [pnpm.io](https://pnpm.io/installation).

### uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or see [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).

## Install dependencies

From the repository root:

```bash
pnpm install
cd apps/api && uv sync && cd ../..
```

`uv sync` creates a local `.venv` in `apps/api` and installs Python dependencies from `pyproject.toml`.

### Database (Phase 1A)

```bash
# Start PostgreSQL 18
docker compose -f infra/docker-compose.yml up -d

# Configure and migrate (from apps/api)
cp .env.example .env
pnpm db:migrate
```

See `apps/api/README.md` for migration and database test details.

## Development

Start all workspace dev servers via Turborepo:

```bash
pnpm dev
```

Or run individually:

```bash
# Frontend (http://localhost:3002)
pnpm --filter @agentic-travel-engine/web dev

# Backend (http://localhost:8000)
pnpm --filter @agentic-travel-engine/api dev
```

The frontend uses **port 3002** because ports 3000 and 3001 are reserved for other local projects.

## Build

```bash
pnpm build
```

## Test

```bash
pnpm test
```

## Lint

```bash
pnpm lint
```

## Type check

```bash
pnpm type-check
```

## Repository structure

```text
/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   ├── shared-types/ # Shared TypeScript types (future OpenAPI contracts)
│   └── mcp-tools/    # MCP tool package boundary
├── infra/            # Future infrastructure-as-code
├── evals/            # Future agent evaluation suites
├── package.json
├── pnpm-workspace.yaml
└── turbo.json
```

## Architecture

```text
Next.js frontend
        ↓
FastAPI API
        ↓
LangGraph orchestration (future)
        ↓
Typed application/domain services (future)
        ↓
MCP tools + RAG + deterministic engines (future)
        ↓
External providers / infrastructure (future)
```

This foundation establishes package boundaries only. Trip-planning features are implemented in later phases.
