import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import type { ReactNode } from "react";

import {
  formatDateRange,
  formatMoney,
  getBudgetHealth,
} from "@/lib/planner/format";
import { cn } from "@/lib/utils";

interface TripHeaderProps {
  run: AgentRunResponse;
  className?: string;
  trace?: ReactNode;
}

export function TripHeader({ run, className, trace }: TripHeaderProps) {
  const trip = run.trip_request;
  const budget = run.budget;
  const destination = trip?.destination ?? "Your trip";
  const travelers = trip?.travelers ?? 1;
  const duration = trip?.duration_days;
  const dateLabel = duration
    ? `${duration} day${duration === 1 ? "" : "s"}`
    : formatDateRange(
        trip?.start_date ?? null,
        trip?.end_date ?? null,
        duration ?? null,
      );
  const health = budget ? getBudgetHealth(budget) : null;
  const route =
    trip?.departure_city && trip.destination
      ? `${trip.departure_city} → ${trip.destination}`
      : trip?.departure_city
        ? `from ${trip.departure_city}`
        : null;

  return (
    <header className={cn("flex min-w-0 items-start justify-between gap-4", className)}>
      <div className="min-w-0 space-y-2">
        <h1 className="font-display text-[2.25rem] leading-[0.92] tracking-tight text-[var(--foreground)] md:text-[2.75rem]">
          {destination}
        </h1>
        <p className="text-sm leading-snug text-[var(--foreground-secondary)]">
          {dateLabel} · {travelers} traveler{travelers === 1 ? "" : "s"}
          {route ? ` · ${route}` : ""}
        </p>
        {budget ? (
          <div className="pt-1" aria-label="Budget summary">
            <p className="font-display text-[1.5rem] leading-none tabular-nums text-[var(--foreground)] md:text-[1.65rem]">
              {formatMoney(budget.total_cost, budget.currency)}
            </p>
            <p
              className={cn(
                "mt-1.5 text-sm tabular-nums",
                health === "over"
                  ? "font-medium text-[var(--budget-over-fg)]"
                  : health === "near"
                    ? "text-[var(--budget-near-fg)]"
                    : "text-[var(--foreground-secondary)]",
              )}
            >
              {health === "over"
                ? `Over budget by ${formatMoney(
                    Math.abs(Number(budget.remaining)),
                    budget.currency,
                  )}`
                : `${formatMoney(budget.remaining, budget.currency)} remaining`}
              <span className="text-[var(--foreground-muted)]">
                {" "}
                · of {formatMoney(budget.budget_amount, budget.currency)}
              </span>
            </p>
          </div>
        ) : null}
      </div>
      {trace ? <div className="shrink-0 pt-1">{trace}</div> : null}
    </header>
  );
}
