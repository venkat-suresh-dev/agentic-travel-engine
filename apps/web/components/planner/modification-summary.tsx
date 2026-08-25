import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import { Hotel, Plane } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ModificationSummaryProps {
  run: AgentRunResponse;
  compact?: boolean;
  className?: string;
}

export function ModificationSummary({
  run,
  compact = true,
  className,
}: ModificationSummaryProps) {
  if (run.operation.operation_type !== "modification") {
    return null;
  }

  const { operation } = run;
  const succeeded = run.status === "complete";
  const affectedDays = operation.affected_days;
  const refreshed = operation.refreshed_sources;

  if (compact) {
    return (
      <section
        className={cn(
          "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-[var(--accent)]/20 bg-[var(--accent)]/5 px-4 py-2.5",
          className,
        )}
        aria-label="Modification summary"
      >
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--accent)]">
          {succeeded ? "Updated" : "Not applied"}
        </p>
        {affectedDays.length > 0 ? (
          <span className="text-sm text-[var(--foreground)]">
            {affectedDays.map((day) => `Day ${day}`).join(", ")}
          </span>
        ) : null}
        {operation.budget_changed ? (
          <Badge variant="warning">Budget recalculated</Badge>
        ) : (
          <span className="text-xs text-[var(--foreground-muted)]">Budget unchanged</span>
        )}
        <span className="inline-flex items-center gap-1 text-xs text-[var(--foreground-secondary)]">
          <Plane className="h-3 w-3" aria-hidden />
          {refreshed.includes("flights") ? "Flights refreshed" : "Flights unchanged"}
        </span>
        <span className="inline-flex items-center gap-1 text-xs text-[var(--foreground-secondary)]">
          <Hotel className="h-3 w-3" aria-hidden />
          {refreshed.includes("hotels") ? "Hotel refreshed" : "Hotel unchanged"}
        </span>
        {operation.summary ? (
          <p className="w-full text-xs text-[var(--foreground-muted)]">{operation.summary}</p>
        ) : null}
      </section>
    );
  }

  return (
    <section
      className={cn(
        "rounded-[2rem] border border-[var(--border)] bg-[var(--surface-elevated)] p-6 shadow-[var(--shadow-soft)]",
        className,
      )}
      aria-labelledby="changes-heading"
    >
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
        What changed
      </p>
      <h2 id="changes-heading" className="mt-2 font-display text-2xl">
        {succeeded ? "Updated" : "Change not applied"}
      </h2>
      {operation.summary ? (
        <p className="mt-2 text-sm text-[var(--foreground-secondary)]">
          {operation.summary}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        {affectedDays.map((day) => (
          <Badge key={day} variant="default">
            Day {day}
          </Badge>
        ))}
        {operation.budget_changed ? (
          <Badge variant="warning">Budget recalculated</Badge>
        ) : null}
      </div>
    </section>
  );
}
