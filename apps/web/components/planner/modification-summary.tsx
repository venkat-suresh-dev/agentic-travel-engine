import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import { ArrowRight, Hotel, Plane, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ModificationSummaryProps {
  run: AgentRunResponse;
  className?: string;
}

export function ModificationSummary({ run, className }: ModificationSummaryProps) {
  if (run.operation.operation_type !== "modification") {
    return null;
  }

  const { operation } = run;
  const succeeded = run.status === "complete";
  const affectedDays = operation.affected_days;
  const refreshed = operation.refreshed_sources;

  return (
    <section
      className={cn(
        "rounded-[2rem] border border-[var(--border)] bg-[var(--surface-elevated)] p-6 shadow-[var(--shadow-soft)]",
        className,
      )}
      aria-labelledby="changes-heading"
    >
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-[var(--accent)]" aria-hidden />
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
          What changed
        </p>
      </div>
      <h2 id="changes-heading" className="mt-2 font-display text-2xl">
        {succeeded ? "Updated" : "Change not applied"}
      </h2>
      {operation.summary ? (
        <p className="mt-2 text-sm text-[var(--foreground-secondary)]">
          {operation.summary}
        </p>
      ) : null}

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <ChangeCard
          title="Days"
          value={
            affectedDays.length
              ? affectedDays.map((day) => `Day ${day}`).join(", ")
              : "No day-level changes"
          }
        />
        <ChangeCard
          title="Budget"
          value={operation.budget_changed ? "Recalculated" : "Unchanged"}
        />
        <ChangeCard
          title="Flights"
          value={refreshed.includes("flights") ? "Refreshed" : "Unchanged"}
          icon={Plane}
        />
        <ChangeCard
          title="Hotel"
          value={refreshed.includes("hotels") ? "Refreshed" : "Unchanged"}
          icon={Hotel}
        />
      </div>

      {refreshed.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {refreshed.map((source) => (
            <Badge key={source} variant="cached">
              Refreshed · {source}
            </Badge>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ChangeCard({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: string;
  icon?: typeof Plane;
}) {
  return (
    <div className="rounded-2xl bg-[var(--surface)] p-4 ring-1 ring-[var(--border)]">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
          {title}
        </p>
        {Icon ? <Icon className="h-4 w-4 text-[var(--foreground-muted)]" /> : null}
      </div>
      <p className="mt-2 flex items-center gap-2 text-sm font-medium">
        {value}
        <ArrowRight className="h-3.5 w-3.5 text-[var(--foreground-muted)]" aria-hidden />
      </p>
    </div>
  );
}
