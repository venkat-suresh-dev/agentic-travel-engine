"use client";

import { PlannerEmptyState } from "@/components/planner/planner-empty-state";
import {
  usePlannerErrorMessage,
  useStartPlannerRun,
} from "@/lib/planner/hooks";

export default function PlannerPage() {
  const startRun = useStartPlannerRun();
  const errorMessage = usePlannerErrorMessage(startRun.error);

  async function handleSubmit(message: string) {
    const runId = crypto.randomUUID();
    await startRun.mutateAsync({ message, runId });
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {startRun.isError ? (
        <p role="alert" className="mb-3 shrink-0 text-sm text-[var(--budget-over-fg)]">
          {errorMessage}
        </p>
      ) : null}
      <PlannerEmptyState onSubmit={handleSubmit} className="min-h-0 flex-1" />
    </div>
  );
}
