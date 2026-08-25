"use client";

import type { AgentRunEvent } from "@agentic-travel-engine/shared-types";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  initialLiveExecutionState,
  reduceLiveExecutionState,
  type LiveExecutionState,
} from "@/lib/planner/execution-state";
import { consumeAgentRunStream } from "@/lib/planner/sse";
import { usePlannerToken } from "@/lib/planner/auth";

interface UseAgentRunStreamOptions {
  runId: string | null;
  enabled?: boolean;
}

export function useAgentRunStream({
  runId,
  enabled = true,
}: UseAgentRunStreamOptions) {
  const getToken = usePlannerToken();
  const [state, setState] = useState<LiveExecutionState>(
    initialLiveExecutionState,
  );
  const [error, setError] = useState<Error | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setState(initialLiveExecutionState);
    setError(null);
  }, []);

  useEffect(() => {
    if (!runId || !enabled) {
      abortRef.current?.abort();
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    void (async () => {
      const token = await getToken();
      await consumeAgentRunStream({
        runId,
        token,
        signal: controller.signal,
        onEvent: (event: AgentRunEvent) => {
          setState((current) => reduceLiveExecutionState(current, event));
        },
        onError: (streamError) => {
          if (!controller.signal.aborted) {
            setError(streamError);
          }
        },
      });
    })();

    return () => {
      controller.abort();
    };
  }, [runId, enabled, getToken]);

  return { execution: state, error, reset };
}
