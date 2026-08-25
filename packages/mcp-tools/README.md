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

## Hotel search tool

- **Server name:** `agentic-travel-hotels`
- **Tool name:** `search_hotels`

### Provider selection

**Amadeus Hotel Search** was selected because:

- The project already uses Amadeus OAuth2 credentials for flights (Phase 3B).
- Amadeus exposes official Hotel List (`/v1/reference-data/locations/hotels/by-city`) and Hotel Search v3 (`/v3/shopping/hotel-offers`) APIs with programmatic search, hotel identity, room/rate data, and exact pricing.
- The same `HotelProvider` abstraction allows swapping to another hotel API without changing LangGraph contracts.

> Note: Amadeus Self-Service portal access has been decommissioned; production deployments should use Amadeus Enterprise credentials. The provider abstraction supports replacement without graph changes.

### Request

| Field | Type | Description |
|-------|------|-------------|
| `location` | string | Human-readable destination (e.g. city name) |
| `city_code` | string | IATA city code resolved from location |
| `check_in` | date | Hotel check-in date |
| `check_out` | date | Hotel check-out date (exclusive) |
| `travelers` | int | Number of adult travelers (≥ 1) |
| `rooms` | int | Number of rooms (≥ 1) |
| `currency` | string | ISO 4217 currency for provider pricing |

### Response

Normalized `HotelSearchResult` with:

- `hotels[]` — normalized hotels with identity, location, room/rate options, exact `Decimal` nightly/total prices + currency
- `source` — `amadeus`
- `retrieved_at` — UTC timestamp
- `data_status` — `live`, `cached`, or `unavailable`
- `disclaimer` — search results are not booking or availability guarantees

### Amadeus authentication

Reuses the same OAuth2 client credentials as flights (`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`).

**Hotel List:** `GET /v1/reference-data/locations/hotels/by-city?cityCode=...` — resolves hotels in a city to Amadeus `hotelId` values.

**Hotel Search v3:** `GET /v3/shopping/hotel-offers?hotelIds=...&adults=...&roomQuantity=...&checkInDate=...&checkOutDate=...&currency=...` — returns room/rate offers with per-night and total pricing where available.

**City resolution:** `GET /v1/reference-data/locations?keyword=...&subType=CITY` when city names must be resolved to IATA codes.

### Provider architecture

```text
search_hotels (MCP)
    ↓
HotelService
    ↓
HotelProvider → AmadeusHotelProvider
CityCodeResolver → AmadeusCityCodeResolver (application layer)
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
  └── no cache → unavailable (no invented hotels)
```

### Cache

- In-process TTL cache (default **2 minutes**, max **128** entries)
- Key: `location|city_code|check_in|check_out|travelers|rooms|currency`
- Hotel pricing and availability change faster than flights; TTL is intentionally shorter than the 5-minute flight cache
- Intended production upgrade: Redis-backed cache governed by provider Terms of Service
- Currency conversion is **not** performed; provider currency is preserved exactly

### Price semantics

- `nightly_price` is populated only when the provider supplies an explicit average/base nightly rate (e.g. `price.variations.average.base`).
- `total_price` reflects the provider-supplied stay total.
- One price is never manufactured from the other unless the underlying provider fields are explicit.

### Availability disclaimer

Search results represent information returned at retrieval time. The system does not guarantee room availability, pricing, or bookability.

## Distance matrix tool

- **Server name:** `agentic-travel-distance`
- **Tool name:** `get_distance_matrix`

### Provider selection

**OpenRouteService Matrix API** was selected because:

- Official first-party API built on OpenStreetMap data with a clear matrix contract
- Supports driving and walking profiles with distance (meters) and duration (seconds)
- Free-tier API key suitable for portfolio/POC use
- Reuses Open-Meteo geocoding (already in the project) for location resolution
- Provider abstraction allows replacement without changing LangGraph contracts

> Note: Production deployments should monitor OpenRouteService rate limits and Terms of Service. The provider abstraction supports swapping to another matrix API.

### Request

| Field | Type | Description |
|-------|------|-------------|
| `origins` | `LocationPoint[]` | Origin locations with `name`, `latitude`, `longitude` |
| `destinations` | `LocationPoint[]` | Destination locations with coordinates |
| `travel_mode` | enum | `driving` or `walking` |

### Response

Normalized `DistanceMatrixResult` with:

- `routes[]` — per origin/destination pairs with `distance_meters` (int) and `duration_seconds` (int)
- `travel_mode` — requested mode
- `source` — `openrouteservice`
- `retrieved_at` — UTC timestamp
- `data_status` — `live`, `cached`, or `unavailable`

### Authentication

API key via `Authorization` header (`OPENROUTESERVICE_API_KEY`).

**Matrix endpoint:** `POST /v2/matrix/{profile}` where profile is `driving-car` or `foot-walking`.

**Location resolution:** Open-Meteo geocoding (`GeocodingLocationResolver`) converts city names to coordinates at the application layer.

### Supported travel modes

| Normalized mode | OpenRouteService profile |
|-----------------|--------------------------|
| `driving` | `driving-car` |
| `walking` | `foot-walking` |

### Provider architecture

```text
get_distance_matrix (MCP)
    ↓
DistanceService
    ↓
DistanceProvider → OpenRouteServiceDistanceProvider
LocationResolver → GeocodingLocationResolver (application layer)
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
  └── no cache → unavailable (no invented distances)
```

### Cache

- In-process TTL cache (default **10 minutes**, max **128** entries)
- Key: `origins>>destinations>>travel_mode` (normalized coordinates included)
- Route geometry is more stable than hotel/flight pricing; TTL is longer than hotels
- Intended production upgrade: Redis-backed cache governed by provider Terms of Service

### Graph integration limitation

The current graph supplies only validated `departure_city` → `destination` as a 1×1 matrix. Attraction/hotel/stop matrices are deferred to itinerary phases.

## Places tools (restaurants and attractions)

- **Server name:** `agentic-travel-places`
- **Tool names:** `search_restaurants`, `search_attractions`

### Provider selection

**Google Places API (New)** was selected because:

- Official first-party API with current Text Search and Nearby Search endpoints
- Explicit field masks for cost control
- Returns coordinates, ratings, price levels, and opening hours suitable for normalization
- Clear place-type filters for restaurants and attractions
- Provider abstraction allows replacement without changing LangGraph contracts

> Note: Production deployments must monitor Google Places billing SKUs and Terms of Service. Field masks are intentionally minimal.

### Authentication

API key via `X-Goog-Api-Key` header (`GOOGLE_PLACES_API_KEY`).

**Restaurant search:** `POST /v1/places:searchText` with `includedType: restaurant`, controlled `textQuery` from validated cuisine enums, `locationBias` circle, and optional `priceLevels`.

**Attraction search:** `POST /v1/places:searchNearby` with explicit `includedTypes` from validated `AttractionCategory` values and `locationRestriction` circle.

**Location resolution:** Reuses `LocationResolver` / Open-Meteo geocoding at the application layer from the validated destination.

### Restaurant request

| Field | Type | Description |
|-------|------|-------------|
| `location` | `SearchLocation` | `name`, `latitude`, `longitude` |
| `radius_meters` | int | Search bias radius (100–50,000) |
| `cuisine` | enum? | Controlled cuisine filter |
| `price_levels` | enum[]? | Price preference |
| `max_results` | int | 1–20 |
| `language_code` / `region_code` | str? | Optional locale hints |

### Attraction request

| Field | Type | Description |
|-------|------|-------------|
| `location` | `SearchLocation` | `name`, `latitude`, `longitude` |
| `radius_meters` | int | Search radius (100–50,000) |
| `categories` | enum[] | Explicit attraction categories |
| `max_results` | int | 1–20 |
| `language_code` / `region_code` | str? | Optional locale hints |

### Field masks

Restaurant and attraction searches use separate explicit field masks. Wildcard `*` is rejected. Reviews, photos, generative summaries, and menus are excluded.

### Resilience

Same pattern as other MCP tools: 5s timeout, one retry with 200ms backoff, 10-minute in-process cache (max 128 entries), `live` / `cached` / `unavailable` provenance.

### Graph integration limitation

The current graph searches restaurants and attractions near the validated destination only. No invented neighborhoods, hotel locations, or itinerary stops.

## Tests

```bash
cd packages/mcp-tools
uv sync
uv run pytest
```

Standard tests use fake providers and fixture payloads. No live Amadeus calls are required.
