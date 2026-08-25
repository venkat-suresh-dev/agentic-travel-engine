# MCP Tools

Python MCP tool servers for the AI Trip Planner.

## MCP SDK

This package uses the official **MCP Python SDK v2** (`mcp>=2.0.0`), supporting the 2026-07-28 Model Context Protocol specification.

## Weather tool

- **Server name:** `agentic-travel-weather`
- **Tool name:** `get_weather_forecast`

See `src/mcp_tools/weather/` for schemas, Open-Meteo provider, cache, and resilience behavior.

## Flight search tool

- **Server name:** `agentic-travel-flights`
- **Tool name:** `search_flights`

### Request

| Field | Type | Description |
|-------|------|-------------|
| `origin` | string | IATA origin code |
| `destination` | string | IATA destination code |
| `departure_date` | date | Outbound departure date |
| `return_date` | date (optional) | Return date for round trips |
| `travelers` | int | Number of adult travelers (≥ 1) |
| `cabin_class` | enum | `ECONOMY`, `PREMIUM_ECONOMY`, `BUSINESS`, `FIRST` |
| `currency` | string | ISO 4217 currency for provider pricing |

### Response

Normalized `FlightSearchResult` with:

- `offers[]` — normalized offers with segments, stops, duration, carrier, exact `Decimal` price + currency
- `source` — `amadeus`
- `retrieved_at` — UTC timestamp
- `data_status` — `live`, `cached`, or `unavailable`
- `disclaimer` — search results are not booking guarantees

### Amadeus authentication

Amadeus uses OAuth2 client credentials:

1. `POST /v1/security/oauth2/token` with `grant_type=client_credentials`, `client_id`, `client_secret`
2. Bearer token (~30 minutes) used for subsequent API calls
3. Tokens are cached server-side and refreshed before expiry

**Flight Offers Search:** `GET /v2/shopping/flight-offers` with origin/destination IATA codes, dates, adults, travel class, and currency.

**Airport resolution:** `GET /v1/reference-data/locations` when city names must be resolved to IATA codes.

Credentials are configured via environment variables in `apps/api` (`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`). Never expose credentials to the frontend.

> Note: Amadeus Self-Service portal access has been decommissioned; production deployments should use Amadeus Enterprise credentials. The provider abstraction allows swapping to another flight API without changing LangGraph contracts.

### Provider architecture

```text
search_flights (MCP)
    ↓
FlightService
    ↓
FlightProvider → AmadeusFlightProvider
AirportCodeResolver → AmadeusAirportCodeResolver (optional)
```

### Resilience

```text
request
  ↓
timeout (5s per HTTP call, configurable)
  ↓
retry once with 200ms backoff
  ↓
still failing?
  ├── fresh in-process cache → cached result
  └── no cache → unavailable (no invented flights)
```

### Cache

- In-process TTL cache (default **5 minutes**, max **128** entries)
- Key: `origin|destination|departure|return|travelers|cabin|currency`
- Flight pricing changes faster than weather; TTL is intentionally shorter
- Intended production upgrade: Redis-backed cache governed by provider Terms of Service
- Currency conversion is **not** performed; provider currency is preserved exactly

## Tests

```bash
cd packages/mcp-tools
uv sync
uv run pytest
```

Standard tests use fake providers and fixture payloads. No live Amadeus calls are required.
