import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";

import { Badge } from "@/components/ui/badge";
import { formatDateRange, formatMoney, getBudgetHealth } from "@/lib/planner/format";
import { cn } from "@/lib/utils";

interface TripHeaderProps {
  run: AgentRunResponse;
  className?: string;
}

function statusLabel(status: AgentRunResponse["status"]): string {
  if (status === "complete") return "Ready";
  if (status === "needs_clarification") return "Needs details";
  return "Attention required";
}

export function TripHeader({ run, className }: TripHeaderProps) {
  const trip = run.trip_request;
  const budget = run.budget;
  const destination = trip?.destination ?? "Your trip";
  const travelers = trip?.travelers ?? 1;
  const duration = trip?.duration_days;
  const dateLabel = formatDateRange(
    trip?.start_date ?? null,
    trip?.end_date ?? null,
    duration ?? null,
  );
  const health = budget ? getBudgetHealth(budget) : null;
  const summary =
    run.operation.summary && run.operation.operation_type === "initial_plan"
      ? run.operation.summary
      : null;

  return (
    <header
      className={cn(
        "rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] px-4 py-3 shadow-[var(--shadow-soft)] md:px-5",
        className,
      )}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={run.status === "complete" ? "success" : "warning"}>
              {statusLabel(run.status)}
            </Badge>
            {trip?.trip_type ? (
              <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                {trip.trip_type}
              </span>
            ) : null}
          </div>
          <h1 className="mt-1 font-display text-2xl leading-tight tracking-tight text-[var(--foreground)] md:text-3xl">
            {destination}
          </h1>
          <p className="mt-0.5 text-sm text-[var(--foreground-secondary)]">
            {dateLabel} · {travelers} traveler{travelers === 1 ? "" : "s"}
            {trip?.departure_city ? ` · from ${trip.departure_city}` : ""}
          </p>
          {summary ? (
            <p className="mt-1 line-clamp-2 text-sm text-[var(--foreground-muted)]">
              {summary}
            </p>
          ) : null}
        </div>

        {budget ? (
          <div className="flex shrink-0 items-end gap-4 border-t border-[var(--border)] pt-3 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-5">
            <div>
              <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Estimate
              </p>
              <p className="font-display text-2xl leading-none text-[var(--foreground)]">
                {formatMoney(budget.total_cost, budget.currency)}
              </p>
              <p className="mt-0.5 text-xs text-[var(--foreground-secondary)]">
                of {formatMoney(budget.budget_amount, budget.currency)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Remaining
              </p>
              <p className="text-lg font-medium text-[var(--foreground)]">
                {formatMoney(budget.remaining, budget.currency)}
              </p>
              {health === "near" ? (
                <p className="text-xs text-[var(--budget-near-fg)]">Near budget</p>
              ) : health === "over" ? (
                <p className="text-xs text-[var(--budget-over-fg)]">Over budget</p>
              ) : (
                <p className="text-xs text-[var(--budget-under-fg)]">On track</p>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </header>
  );
}
