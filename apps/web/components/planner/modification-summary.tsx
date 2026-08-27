import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";

import { cn } from "@/lib/utils";

interface ModificationSummaryProps {
  run: AgentRunResponse;
  compact?: boolean;
  className?: string;
}

export function ModificationSummary({
  run,
  className,
}: ModificationSummaryProps) {
  if (run.operation.operation_type !== "modification") {
    return null;
  }

  const { operation } = run;
  const succeeded = run.status === "complete";
  const affectedDays = operation.affected_days;
  const facts = operation.change_facts ?? [];
  const title = succeeded
    ? affectedDays.length === 1
      ? `Day ${String(affectedDays[0]).padStart(2, "0")} updated`
      : "Trip updated"
    : "Not applied";

  return (
    <section
      className={cn(
        "rounded-xl bg-[var(--accent)]/[0.05] px-4 py-3",
        className,
      )}
      aria-label="Modification summary"
    >
      <p className="text-sm font-medium text-[var(--accent)]">{title}</p>
      {facts.length > 0 ? (
        <ul className="mt-2 space-y-1">
          {facts.map((fact) => (
            <li key={fact} className="text-sm text-[var(--foreground-secondary)]">
              {fact}
            </li>
          ))}
        </ul>
      ) : affectedDays.length > 0 ? (
        <p className="mt-1.5 text-sm text-[var(--foreground-secondary)]">
          {affectedDays.map((day) => `Day ${day}`).join(", ")}
        </p>
      ) : null}
    </section>
  );
}
