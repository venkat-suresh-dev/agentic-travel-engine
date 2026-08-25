import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";

const RUN_PREFIX = "planner-run:";
const HISTORY_PREFIX = "planner-history:";

export interface ConversationEntry {
  id: string;
  role: "user" | "system";
  kind: "request" | "clarification" | "status" | "modification" | "error";
  content: string;
  timestamp: string;
}

export interface PlannerSession {
  run: AgentRunResponse;
  history: ConversationEntry[];
}

function runKey(runId: string) {
  return `${RUN_PREFIX}${runId}`;
}

function historyKey(runId: string) {
  return `${HISTORY_PREFIX}${runId}`;
}

export function loadPlannerSession(runId: string): PlannerSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const runRaw = sessionStorage.getItem(runKey(runId));
  const historyRaw = sessionStorage.getItem(historyKey(runId));
  if (!runRaw) {
    return null;
  }
  try {
    return {
      run: JSON.parse(runRaw) as AgentRunResponse,
      history: historyRaw ? (JSON.parse(historyRaw) as ConversationEntry[]) : [],
    };
  } catch {
    return null;
  }
}

export function savePlannerSession(session: PlannerSession): void {
  if (typeof window === "undefined") {
    return;
  }
  sessionStorage.setItem(runKey(session.run.run_id), JSON.stringify(session.run));
  sessionStorage.setItem(
    historyKey(session.run.run_id),
    JSON.stringify(session.history),
  );
}

export function appendHistoryEntry(
  runId: string,
  entry: ConversationEntry,
): ConversationEntry[] {
  const existing = loadPlannerSession(runId);
  const history = [...(existing?.history ?? []), entry];
  if (existing) {
    savePlannerSession({ ...existing, history });
  } else {
    sessionStorage.setItem(historyKey(runId), JSON.stringify(history));
  }
  return history;
}
