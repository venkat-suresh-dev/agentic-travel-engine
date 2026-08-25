import type {
  AgentRunCreateRequest,
  AgentRunMessageRequest,
  AgentRunResponse,
} from "@agentic-travel-engine/shared-types";

import { apiFetch } from "@/lib/api/client";

export async function createAgentRun(
  payload: AgentRunCreateRequest,
  token: string | null,
): Promise<AgentRunResponse> {
  return apiFetch<AgentRunResponse>("/api/agent/runs", {
    method: "POST",
    body: JSON.stringify(payload),
    token,
  });
}

export async function fetchAgentRun(
  runId: string,
  token: string | null,
): Promise<AgentRunResponse> {
  return apiFetch<AgentRunResponse>(`/api/agent/runs/${runId}`, {
    method: "GET",
    token,
  });
}

export async function sendAgentRunMessage(
  runId: string,
  payload: AgentRunMessageRequest,
  token: string | null,
): Promise<AgentRunResponse> {
  return apiFetch<AgentRunResponse>(`/api/agent/runs/${runId}/messages`, {
    method: "POST",
    body: JSON.stringify(payload),
    token,
  });
}
