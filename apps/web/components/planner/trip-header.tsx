import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";

import { Badge } from "@/components/ui/badge";
import { formatDateRange, formatMoney } from "@/lib/planner/format";
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

  return (
    <header
      className={cn(
        "relative overflow-hidden rounded-[2rem] border border-[var(--border)] bg-[var(--surface-elevated)] px-6 py-8 shadow-[var(--shadow-soft)] md:px-8",
        className,
      )}
    >
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(13,92,99,0.08),transparent_55%)]"
        aria-hidden
      />
      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={run.status === "complete" ? "success" : "warning"}>
              {statusLabel(run.status)}
            </Badge>
            {trip?.trip_type ? (
              <span className="text-xs uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
                {trip.trip_type}
              </span>
            ) : null}
          </div>
          <h1 className="font-display text-4xl leading-none tracking-tight text-[var(--foreground)] md:text-5xl">
            {destination}
          </h1>
          <p className="text-sm text-[var(--foreground-secondary)]">
            {dateLabel} · {travelers} traveler{travelers === 1 ? "" : "s"}
            {trip?.departure_city ? ` · from ${trip.departure_city}` : ""}
          </p>
        </div>
        {budget ? (
          <div className="min-w-[220px] rounded-2xl bg-[var(--surface)] px-5 py-4 ring-1 ring-[var(--border)]">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
              Estimated total
            </p>
            <p className="mt-1 font-display text-3xl text-[var(--foreground)]">
              {formatMoney(budget.total_cost, budget.currency)}
            </p>
            <p className="mt-1 text-sm text-[var(--foreground-secondary)]">
              {formatMoney(budget.remaining, budget.currency)} remaining of{" "}
              {formatMoney(budget.budget_amount, budget.currency)}
            </p>
          </div>
        ) : null}
      </div>
    </header>
  );
}
