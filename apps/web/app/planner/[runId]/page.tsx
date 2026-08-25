"use client";

import { use, useEffect } from "react";

import { FailureBanner } from "@/components/planner/failure-banner";
import { LivePlanningState } from "@/components/planner/live-planning-state";
import { PlannerWorkspace } from "@/components/planner/planner-workspace";
import {
  usePendingPlannerStart,
  usePlannerErrorMessage,
  usePlannerSession,
  useSendPlannerMessage,
} from "@/lib/planner/hooks";
import { loadPendingPlannerStart } from "@/lib/planner/storage";
import { useAgentRunStream } from "@/lib/planner/use-agent-run-stream";

export default function PlannerRunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = use(params);
  const pendingStart = loadPendingPlannerStart(runId);
  const pendingPlannerStart = usePendingPlannerStart(runId);
  const { data: session, isLoading, isError, error, isFetching } =
    usePlannerSession(runId, { enabled: !pendingStart });
  const sendMessage = useSendPlannerMessage(runId);
  const isStarting = pendingPlannerStart.isPending;
  const isMutating = sendMessage.isPending || isStarting;
  const { execution } = useAgentRunStream({
    runId,
    enabled: isMutating || Boolean(session),
  });
  const hydrationErrorMessage = usePlannerErrorMessage(error);
  const mutationErrorMessage = usePlannerErrorMessage(
    sendMessage.error ?? pendingPlannerStart.error,
  );

  useEffect(() => {
    if (pendingStart && !pendingPlannerStart.isPending && !pendingPlannerStart.isSuccess) {
      void pendingPlannerStart.mutateAsync();
    }
  }, [pendingStart, pendingPlannerStart]);

  const planningMode =
    session?.run.operation.operation_type === "modification"
      ? "modification"
      : session?.run.operation.operation_type === "clarification"
        ? "clarification"
        : "initial";

  async function handleSendMessage(message: string) {
    await sendMessage.mutateAsync(message);
  }

  if (isError && !session) {
    return (
      <FailureBanner
        title="This planning session is unavailable"
        message={hydrationErrorMessage}
      />
    );
  }

  if ((isLoading || isStarting) && !session) {
    return (
      <div className="mx-auto max-w-2xl">
        <LivePlanningState execution={execution} mode="initial" />
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
      {isFetching && !isMutating ? (
        <p className="text-xs uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
          Refreshing trip state…
        </p>
      ) : null}
      {sendMessage.isError || pendingPlannerStart.isError ? (
        <p role="alert" className="text-sm text-[var(--budget-over-fg)]">
          {mutationErrorMessage}
        </p>
      ) : null}
      <PlannerWorkspace
        session={session}
        isMutating={isMutating}
        planningMode={planningMode}
        execution={execution}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
