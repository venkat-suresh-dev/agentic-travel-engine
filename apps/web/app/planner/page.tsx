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
      <div className="mx-auto max-w-2xl">
        <PlanningState
          activePhase={phases[phaseIndex] ?? "building"}
          mode="initial"
        />
      </div>
    );
  }

  return (
    <div>
      {startRun.isError ? (
        <p role="alert" className="mb-4 text-sm text-[var(--budget-over-fg)]">
          {errorMessage}
        </p>
      ) : null}
      <PlannerEmptyState onSubmit={handleSubmit} />
    </div>
  );
}
