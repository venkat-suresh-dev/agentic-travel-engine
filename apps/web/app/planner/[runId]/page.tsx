"use client";

import { use, useState } from "react";

import { FailureBanner } from "@/components/planner/failure-banner";
import { PlannerWorkspace } from "@/components/planner/planner-workspace";
import { PlanningState } from "@/components/planner/planning-state";
import {
  usePlannerErrorMessage,
  usePlannerSession,
  useSendPlannerMessage,
} from "@/lib/planner/hooks";

export default function PlannerRunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = use(params);
  const { data: session, isLoading, isError, error, isFetching } =
    usePlannerSession(runId);
  const sendMessage = useSendPlannerMessage(runId);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const phases = [
    "understanding",
    "searching",
    "weather",
    "building",
    "budget",
    "validating",
  ] as const;
  const hydrationErrorMessage = usePlannerErrorMessage(error);
  const mutationErrorMessage = usePlannerErrorMessage(sendMessage.error);

  const planningMode =
    session?.run.operation.operation_type === "modification"
      ? "modification"
      : session?.run.operation.operation_type === "clarification"
        ? "clarification"
        : "initial";

  async function handleSendMessage(message: string) {
    setPhaseIndex(0);
    const interval = window.setInterval(() => {
      setPhaseIndex((current) => Math.min(current + 1, phases.length - 1));
    }, 600);
    try {
      await sendMessage.mutateAsync(message);
    } finally {
      window.clearInterval(interval);
    }
  }

  if (isError) {
    return (
      <FailureBanner
        title="This planning session is unavailable"
        message={hydrationErrorMessage}
      />
    );
  }

  if (isLoading && !session) {
    return (
      <div className="mx-auto max-w-2xl">
        <PlanningState activePhase="understanding" mode="initial" />
      </div>
    );
  }

  if (!session) {
    return (
      <FailureBanner
        title="This planning session is unavailable"
        message="We could not load this trip from the server. It may have expired after an API restart, or you may not have access."
      />
    );
  }

  return (
    <div className="space-y-4">
      {isFetching && !sendMessage.isPending ? (
        <p className="text-xs uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
          Refreshing trip state…
        </p>
      ) : null}
      {sendMessage.isError ? (
        <p role="alert" className="text-sm text-[var(--budget-over-fg)]">
          {mutationErrorMessage}
        </p>
      ) : null}
      <PlannerWorkspace
        session={session}
        isMutating={sendMessage.isPending}
        planningPhase={phases[phaseIndex] ?? "building"}
        planningMode={planningMode}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
