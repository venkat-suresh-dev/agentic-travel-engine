"use client";

import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";

import { createAgentRun, fetchAgentRun, sendAgentRunMessage } from "@/lib/api/agent";
import { friendlyErrorMessage } from "@/lib/api/errors";
import { usePlannerToken } from "@/lib/planner/auth";
import {
  clearPendingPlannerStart,
  loadPendingPlannerStart,
  loadPlannerSession,
  savePendingPlannerStart,
  savePlannerSession,
  type ConversationEntry,
  type PlannerSession,
} from "@/lib/planner/storage";

export const plannerRunKey = (runId: string) => ["planner-run", runId] as const;

const subscribeClientReady = () => () => {};

export function useClientReady(): boolean {
  return useSyncExternalStore(subscribeClientReady, () => true, () => false);
}

function createEntry(
  role: ConversationEntry["role"],
  kind: ConversationEntry["kind"],
  content: string,
): ConversationEntry {
  return {
    id: crypto.randomUUID(),
    role,
    kind,
    content,
    timestamp: new Date().toISOString(),
  };
}

export function usePlannerSession(
  runId: string,
  options?: { enabled?: boolean; placeholderData?: PlannerSession },
) {
  const getToken = usePlannerToken();

  return useQuery({
    queryKey: plannerRunKey(runId),
    queryFn: async () => {
      const cached = loadPlannerSession(runId);
      const token = await getToken();
      const run = await fetchAgentRun(runId, token);
      const session: PlannerSession = {
        run,
        history: cached?.history ?? [],
      };
      savePlannerSession(session);
      return session;
    },
    placeholderData: options?.placeholderData,
    staleTime: Infinity,
    enabled: options?.enabled ?? Boolean(runId),
  });
}

export function useStartPlannerRun() {
  const router = useRouter();

  return useMutation({
    mutationFn: async ({ message, runId }: { message: string; runId: string }) => {
      savePendingPlannerStart({ runId, message });
      return { runId, message };
    },
    onSuccess: ({ runId }) => {
      router.push(`/planner/${runId}`);
    },
  });
}

export function usePendingPlannerStart(runId: string) {
  const getToken = usePlannerToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ["planner-pending-start", runId],
    mutationFn: async () => {
      const pending = loadPendingPlannerStart(runId);
      if (!pending) {
        return null;
      }
      const token = await getToken();
      const run = await createAgentRun(
        { message: pending.message, run_id: pending.runId },
        token,
      );
      const history: ConversationEntry[] = [
        createEntry("user", "request", pending.message),
        createEntry(
          "system",
          run.status === "needs_clarification" ? "clarification" : "status",
          run.clarification?.message ??
            run.operation.summary ??
            "Planning started.",
        ),
      ];
      const session: PlannerSession = { run, history };
      savePlannerSession(session);
      clearPendingPlannerStart(runId);
      return session;
    },
    onSuccess: (session) => {
      if (session) {
        queryClient.setQueryData(plannerRunKey(runId), session);
      }
    },
  });
}

export function useSendPlannerMessage(runId: string) {
  const getToken = usePlannerToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (message: string) => {
      const token = await getToken();
      const run = await sendAgentRunMessage(runId, { message }, token);
      const existing = loadPlannerSession(runId);
      const history = [
        ...(existing?.history ?? []),
        createEntry("user", "request", message),
        createEntry(
          "system",
          run.operation.operation_type === "modification"
            ? "modification"
            : run.status === "needs_clarification"
              ? "clarification"
              : run.status === "failed"
                ? "error"
                : "status",
          run.operation.summary ??
            run.clarification?.message ??
            run.error ??
            "Trip updated.",
        ),
      ];
      const session: PlannerSession = { run, history };
      savePlannerSession(session);
      return session;
    },
    onSuccess: (session) => {
      queryClient.setQueryData(plannerRunKey(runId), session);
    },
  });
}

export function usePlannerErrorMessage(error: unknown): string {
  return friendlyErrorMessage(error);
}

export function isCompleteRun(run: AgentRunResponse | undefined): boolean {
  return run?.status === "complete" && Boolean(run.itinerary);
}
