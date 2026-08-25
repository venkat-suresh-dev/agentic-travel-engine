# Phase 5C Itinerary Critic

The critic is the final deterministic correctness gate before an itinerary becomes final graph state.

## Responsibilities

- Consume itinerary drafts produced by `build_itinerary`
- Reuse `apps/api/app/itinerary/validator.py` for structural checks
- Add budget consistency, location, and weather-rule checks
- Emit structured `CriticResult` issue codes
- Drive a bounded retry loop without re-running external providers

## Deterministic Validation

The critic never depends on a second LLM call for correctness.

It checks:

- exact day count and day sequence
- candidate and itinerary source integrity
- time ordering, overlaps, and travel buffers
- daily subtotal arithmetic
- budget field consistency with authoritative `BudgetResult`
- meal-per-day requirement
- place-backed coordinates
- rainy-day indoor preference when indoor options exist

`BUDGET_EXCEEDED` is emitted as a warning only. A structurally valid over-budget plan may still pass the critic.

## Retry Model

```text
MAX_ITINERARY_RETRIES = 2
MAX_ITINERARY_ATTEMPTS = 3
```

Graph flow:

```text
build_itinerary → critic_validate
  ├── valid → finalize_run
  ├── invalid + attempts remaining → build_itinerary
  └── invalid + retries exhausted → finalize_failure
```

On retry:

- grounded tool outputs remain in state
- only itinerary composition/materialization reruns
- structured `critic_issues` are passed to the composer through `ItineraryBuildContext.critic_feedback`

External providers (weather, flights, hotels, distance, places, currency, RAG) are not invoked again during retries.

## State Model

- `itinerary_draft` — materialized candidate pending critic approval
- `itinerary_candidate` — structured source-id selection
- `critic_result` — latest deterministic critic output
- `critic_issues` — structured feedback for rebuild
- `itinerary_attempt` — bounded attempt counter
- `itinerary` — populated only after critic approval
- `planning_failed` / `planning_failure` — terminal failure metadata

## Terminal Failure

When retries are exhausted:

- `itinerary` remains unset
- the last candidate/draft remain diagnostic state only
- `planning_failed = true`
- critic issues are preserved for observability

## Phase 6 Handoff

Conversation modification and user-facing explanation layers are out of scope for Phase 5C.
