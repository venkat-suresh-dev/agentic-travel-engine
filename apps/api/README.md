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
