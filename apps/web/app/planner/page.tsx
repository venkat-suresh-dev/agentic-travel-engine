"use client";

import { useState } from "react";

import { PlannerEmptyState } from "@/components/planner/planner-empty-state";
import { PlanningState } from "@/components/planner/planning-state";
import {
  usePlannerErrorMessage,
  useStartPlannerRun,
} from "@/lib/planner/hooks";

export default function PlannerPage() {
  const startRun = useStartPlannerRun();
  const [phaseIndex, setPhaseIndex] = useState(0);
  const phases = [
    "understanding",
    "searching",
    "weather",
    "building",
    "budget",
    "validating",
  ] as const;
  const errorMessage = usePlannerErrorMessage(startRun.error);

  async function handleSubmit(message: string) {
    setPhaseIndex(0);
    const interval = window.setInterval(() => {
      setPhaseIndex((current) => Math.min(current + 1, phases.length - 1));
    }, 700);
    try {
      await startRun.mutateAsync(message);
    } finally {
      window.clearInterval(interval);
    }
  }

  if (startRun.isPending) {
    return (
      <div className="flex flex-1 flex-col justify-center">
        <div className="mx-auto w-full max-w-lg">
          <PlanningState
            activePhase={phases[phaseIndex] ?? "building"}
            mode="initial"
          />
        </div>
      </div>
    );
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
