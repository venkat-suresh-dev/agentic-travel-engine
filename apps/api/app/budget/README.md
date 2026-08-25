# Deterministic Budget Engine (Phase 5A)

The budget engine is the **authoritative** source for trip cost arithmetic in the AI Trip Planner.

```text
Provider facts + explicit assumptions
            ↓
Deterministic Python arithmetic (Decimal)
            ↓
Authoritative BudgetResult
            ↓
LLM may narrate, never calculate
```

## Rules

- All money uses `Decimal` with `quantize_money()` (`ROUND_HALF_UP`, 2dp).
- Provider prices (`flight`, `hotel`) come from normalized MCP tool results.
- Flight budget-currency values use the Phase 3F `CurrencyConversionResult` when available.
- Original provider amounts/currencies are preserved on each category line.
- Food, transport, activity (default), and other categories are explicit **estimates**.
- Unavailable provider data is **excluded** from totals (not treated as zero).
- Free activities are represented with `data_kind=free` and amount `0`.

## Graph integration

```text
convert_currency → compute_budget → finalize_run
```

`compute_budget` is deterministic, has no external API calls, and does not use the LLM.

## Formulas

```text
total_cost = sum(included category amounts in budget currency)
remaining = budget_amount - total_cost
budget_exceeded = total_cost > budget_amount
variance = max(0, total_cost - budget_amount)
```

## Price data kinds

| Kind | Meaning |
| --- | --- |
| `live` | Live provider search result |
| `cached` | Cached provider search result |
| `estimated` | Explicit planning assumption |
| `free` | Explicit zero-cost item |
| `unavailable` | Missing/unconverted provider fact; excluded from total |
