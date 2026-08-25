"use client";

import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { createAgentRun, fetchAgentRun, sendAgentRunMessage } from "@/lib/api/agent";
import { friendlyErrorMessage } from "@/lib/api/errors";
import { usePlannerToken } from "@/lib/planner/auth";
import {
  loadPlannerSession,
  savePlannerSession,
  type ConversationEntry,
  type PlannerSession,
} from "@/lib/planner/storage";

export const plannerRunKey = (runId: string) => ["planner-run", runId] as const;

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

export function usePlannerSession(runId: string) {
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
    placeholderData: () => loadPlannerSession(runId) ?? undefined,
    staleTime: Infinity,
    enabled: Boolean(runId),
  });
}

export function useStartPlannerRun() {
  const getToken = usePlannerToken();
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (message: string) => {
      const token = await getToken();
      const run = await createAgentRun({ message }, token);
      const history: ConversationEntry[] = [
        createEntry("user", "request", message),
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
      return session;
    },
    onSuccess: (session) => {
      queryClient.setQueryData(plannerRunKey(session.run.run_id), session);
      router.push(`/planner/${session.run.run_id}`);
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
