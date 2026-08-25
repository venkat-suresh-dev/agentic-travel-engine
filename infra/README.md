# Infrastructure

Local and future cloud infrastructure for the AI Trip Planner.

## Local PostgreSQL

Start PostgreSQL 18 for local development:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Stop the database:

```bash
docker compose -f infra/docker-compose.yml down
```

### Configuration

Environment variables (with defaults):

| Variable | Default |
|----------|---------|
| `POSTGRES_USER` | `trip_planner` |
| `POSTGRES_PASSWORD` | `trip_planner` |
| `POSTGRES_DB` | `trip_planner` |
| `POSTGRES_PORT` | `5432` |

Copy `apps/api/.env.example` to `apps/api/.env` for application connection settings.

Data is stored in the named Docker volume `agentic-travel-engine-postgres-data-v18`.

## Future scope

- Container definitions for production services
- Cloud deployment manifests
- CI/CD environment configuration
