"use client";

import { use, useEffect } from "react";

import { FailureBanner } from "@/components/planner/failure-banner";
import { LivePlanningState } from "@/components/planner/live-planning-state";
import { PlannerWorkspace } from "@/components/planner/planner-workspace";
import {
  useClientReady,
  usePendingPlannerStart,
  usePlannerErrorMessage,
  usePlannerSession,
  useSendPlannerMessage,
} from "@/lib/planner/hooks";
import { resolvePlannerRunView } from "@/lib/planner/run-view";
import {
  loadPendingPlannerStart,
  loadPlannerSession,
} from "@/lib/planner/storage";
import { useAgentRunStream } from "@/lib/planner/use-agent-run-stream";

export default function PlannerRunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = use(params);
  return <PlannerRunScreen runId={runId} />;
}

export function PlannerRunScreen({ runId }: { runId: string }) {
  const clientReady = useClientReady();
  const pendingStart = clientReady ? loadPendingPlannerStart(runId) : null;
  const placeholderData =
    clientReady && !pendingStart
      ? (loadPlannerSession(runId) ?? undefined)
      : undefined;
  const pendingPlannerStart = usePendingPlannerStart(runId);
  const { data: session, isLoading, isError, error, isFetching } =
    usePlannerSession(runId, {
      enabled: clientReady && !pendingStart,
      placeholderData,
    });
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
  const view = resolvePlannerRunView({
    session,
    isError,
    isLoading,
    isStarting,
    isFetching,
    isMutating,
    clientReady,
    hasPendingStart: Boolean(pendingStart),
    hasMutationError: sendMessage.isError || pendingPlannerStart.isError,
  });

  useEffect(() => {
    if (
      pendingStart &&
      !pendingPlannerStart.isPending &&
      !pendingPlannerStart.isSuccess
    ) {
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

  if (view.kind === "error") {
    return (
      <FailureBanner
        title="This planning session is unavailable"
        message={hydrationErrorMessage}
      />
    );
  }

  if (view.kind === "planning") {
    return (
      <div className="mx-auto flex min-h-0 flex-1 items-start">
        <div className="w-full max-w-2xl">
          <LivePlanningState execution={execution} mode="initial" />
        </div>
      </div>
    );
  }

  if (view.kind === "unavailable") {
    return (
      <FailureBanner
        title="This planning session is unavailable"
        message="We could not load this trip from the server. It may have expired after an API restart, or you may not have access."
      />
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      {view.showRefreshIndicator ? (
        <p
          data-testid="planner-refresh-status"
          className="text-xs uppercase tracking-[0.16em] text-[var(--foreground-muted)]"
        >
          Refreshing trip state…
        </p>
      ) : null}
      {view.showMutationError ? (
        <p role="alert" className="text-sm text-[var(--budget-over-fg)]">
          {mutationErrorMessage}
        </p>
      ) : null}
      {session ? (
        <PlannerWorkspace
          session={session}
          isMutating={isMutating}
          planningMode={planningMode}
          execution={execution}
          onSendMessage={handleSendMessage}
          className="min-h-0 flex-1"
        />
      ) : null}
    </div>
  );
}
