import type { AgentRunEvent } from "@agentic-travel-engine/shared-types";

import { getApiBaseUrl } from "@/lib/api/client";

export interface AgentRunStreamOptions {
  runId: string;
  token: string | null;
  signal?: AbortSignal;
  onEvent: (event: AgentRunEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

function parseSseData(line: string): AgentRunEvent | null {
  if (!line.startsWith("data: ")) {
    return null;
  }
  try {
    return JSON.parse(line.slice(6)) as AgentRunEvent;
  } catch {
    return null;
  }
}

export async function consumeAgentRunStream(
  options: AgentRunStreamOptions,
): Promise<void> {
  const { runId, token, signal, onEvent, onError, onComplete } = options;
  const headers: HeadersInit = {
    Accept: "text/event-stream",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  let response: Response;
  try {
    response = await fetch(
      `${getApiBaseUrl()}/api/agent/runs/${runId}/stream`,
      { headers, signal },
    );
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error(String(error)));
    return;
  }

  if (!response.ok) {
    onError?.(new Error(`Stream failed with status ${response.status}`));
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError?.(new Error("Stream body unavailable"));
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith(":")) {
          continue;
        }
        const event = parseSseData(trimmed);
        if (event) {
          onEvent(event);
          if (
            event.type === "run_completed" ||
            event.type === "run_failed"
          ) {
            onComplete?.();
            return;
          }
        }
      }
    }
    onComplete?.();
  } catch (error) {
    if (signal?.aborted) {
      return;
    }
    onError?.(error instanceof Error ? error : new Error(String(error)));
  } finally {
    reader.releaseLock();
  }
}
