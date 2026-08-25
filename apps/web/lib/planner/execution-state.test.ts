import { describe, expect, it } from "vitest";

import type { AgentRunEvent } from "@agentic-travel-engine/shared-types";

import {
  initialLiveExecutionState,
  reduceLiveExecutionState,
} from "@/lib/planner/execution-state";

function event(
  partial: Partial<AgentRunEvent> & Pick<AgentRunEvent, "type" | "event_id">,
): AgentRunEvent {
  return {
    run_id: "run-1",
    timestamp: "2026-01-01T00:00:00.000Z",
    ...partial,
  };
}

describe("reduceLiveExecutionState", () => {
  it("tracks node and tool lifecycle", () => {
    let state = initialLiveExecutionState;
    state = reduceLiveExecutionState(
      state,
      event({ event_id: "1", type: "run_started" }),
    );
    state = reduceLiveExecutionState(
      state,
      event({
        event_id: "2",
        type: "node_started",
        node_name: "extract_requirements",
      }),
    );
    state = reduceLiveExecutionState(
      state,
      event({
        event_id: "3",
        type: "node_completed",
        node_name: "extract_requirements",
        status: "success",
        duration_ms: 120,
      }),
    );
    state = reduceLiveExecutionState(
      state,
      event({
        event_id: "4",
        type: "tool_started",
        tool_name: "flights",
      }),
    );
    state = reduceLiveExecutionState(
      state,
      event({
        event_id: "5",
        type: "tool_completed",
        tool_name: "flights",
        status: "success",
        duration_ms: 900,
      }),
    );
    state = reduceLiveExecutionState(
      state,
      event({
        event_id: "6",
        type: "run_completed",
        duration_ms: 1800,
      }),
    );

    expect(state.isComplete).toBe(true);
    expect(state.nodes).toHaveLength(1);
    expect(state.tools).toHaveLength(1);
    expect(state.tools[0]?.durationMs).toBe(900);
  });

  it("ignores duplicate events", () => {
    const started = event({ event_id: "dup", type: "run_started" });
    const once = reduceLiveExecutionState(initialLiveExecutionState, started);
    const twice = reduceLiveExecutionState(once, started);
    expect(twice).toBe(once);
  });

  it("marks unavailable tools", () => {
    const state = reduceLiveExecutionState(
      initialLiveExecutionState,
      event({
        event_id: "tool-1",
        type: "tool_completed",
        tool_name: "hotels",
        status: "unavailable",
      }),
    );
    expect(state.tools[0]?.status).toBe("unavailable");
  });
});
