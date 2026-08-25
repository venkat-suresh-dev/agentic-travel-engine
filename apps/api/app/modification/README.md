# Phase 6A Selective Trip Modification

Phase 6A adds targeted trip modifications on top of approved itineraries without regenerating unrelated portions.

## Modification Intents

Supported intents include:

- `CHANGE_PACE` / `MODIFY_DAY` — adjust scheduling for specific days
- `CHANGE_RESTAURANT` / `REDUCE_COST` — swap meal selections
- `CHANGE_ACTIVITY` / `REPLACE_ITEM` — swap attractions
- `CHANGE_HOTEL` — refresh hotel search and accommodation state
- `MODIFY_TRIP_REQUIREMENT` — broad date/requirement invalidation

## Scope and Refresh

`resolve_modification_scope()` deterministically computes:

- affected days and item ids
- whether provider refresh is required
- whether budget recomputation is required
- whether critic validation is required

`build_refresh_plan()` maps scope to the smallest provider refresh set.

## Merge Semantics

- Unaffected days are copied verbatim from the previous itinerary
- Unchanged items keep stable `item_id` values when `source_id` matches
- Infrastructure items remain unless hotel scope changes
- Grounded `source_id` values are preserved or replaced only from catalog data

## Clarification vs Modification

| Context | Detection |
|---|---|
| Incomplete plan clarification | `status == awaiting_user` or incomplete validation |
| Completed plan modification | approved `itinerary` exists, `planning_failed == false`, resume message present |

## Graph Flow

```text
route_entry
  ├── clarification → extract_requirements → ...
  └── modification → extract_modification → resolve_modification_scope
        ├── selective provider refresh → apply_modification
        └── apply_modification → budget recompute (if needed) → critic_validate
```

Failed modifications restore `previous_itinerary` and emit structured `modification_failure`.
