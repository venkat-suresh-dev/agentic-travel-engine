# Weather MCP Tools

Python MCP tool servers for the AI Trip Planner.

## MCP SDK

This package uses the official **MCP Python SDK v2** (`mcp>=2.0.0`), supporting the 2026-07-28 Model Context Protocol specification.

## Weather tool

- **Server name:** `agentic-travel-weather`
- **Tool name:** `get_weather_forecast`

### Request

| Field | Type | Description |
|-------|------|-------------|
| `location` | string | Destination or place name |
| `start_date` | date | Forecast window start |
| `end_date` | date | Forecast window end |

### Response

Normalized `WeatherForecastResult` with:

- `forecast[]` daily rows (temperature, precipitation probability, summary)
- `source` provider identifier (`open-meteo`)
- `retrieved_at` UTC timestamp
- `data_status` (`live`, `cached`, or `unavailable`)

## Provider architecture

```text
get_weather_forecast (MCP)
    ↓
WeatherService
    ↓
GeocodingProvider → OpenMeteoGeocodingProvider
WeatherProvider   → OpenMeteoWeatherProvider
```

Location coordinates are resolved via Open-Meteo geocoding. No destination coordinates are hard-coded.

## Resilience

```text
request
  ↓
timeout (5s per HTTP call)
  ↓
retry once with 200ms backoff
  ↓
still failing?
  ├── fresh in-process cache → cached result
  └── no cache → unavailable (no invented forecast)
```

## Cache

- In-process TTL cache (default **30 minutes**, max **256** entries)
- Key: `location|start_date|end_date`
- Intended production upgrade: Redis-backed cache with the same key scheme

## Running the MCP server

```bash
cd packages/mcp-tools
uv sync
uv run mcp dev src/mcp_tools/weather/mcp_server.py
```

## Tests

```bash
cd packages/mcp-tools
uv run pytest
```

Standard tests use fake providers and do not call live Open-Meteo.
