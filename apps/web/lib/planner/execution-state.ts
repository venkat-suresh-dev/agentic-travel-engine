import type { AgentRunEvent } from "@agentic-travel-engine/shared-types";
import {
  NODE_LABELS,
  TOOL_LABELS,
} from "@agentic-travel-engine/shared-types";

export type ExecutionItemStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "unavailable"
  | "skipped";

export interface ExecutionItem {
  id: string;
  kind: "node" | "tool";
  name: string;
  label: string;
  status: ExecutionItemStatus;
  durationMs: number | null;
  errorMessage?: string;
  dataMode?: string;
  provider?: string | null;
}

export interface LiveExecutionState {
  runId: string | null;
  isActive: boolean;
  isComplete: boolean;
  isFailed: boolean;
  startedAt: string | null;
  completedAt: string | null;
  totalDurationMs: number | null;
  nodes: ExecutionItem[];
  tools: ExecutionItem[];
  parallelActive: boolean;
  seenEventIds: Set<string>;
  summary: Record<string, unknown>;
}

export const initialLiveExecutionState: LiveExecutionState = {
  runId: null,
  isActive: false,
  isComplete: false,
  isFailed: false,
  startedAt: null,
  completedAt: null,
  totalDurationMs: null,
  nodes: [],
  tools: [],
  parallelActive: false,
  seenEventIds: new Set(),
  summary: {},
};

function labelForNode(nodeName: string): string {
  return NODE_LABELS[nodeName] ?? nodeName.replaceAll("_", " ");
}

function labelForTool(toolName: string): string {
  return TOOL_LABELS[toolName] ?? toolName;
}

function upsertItem(
  items: ExecutionItem[],
  item: ExecutionItem,
): ExecutionItem[] {
  const index = items.findIndex((entry) => entry.id === item.id);
  if (index === -1) {
    return [...items, item];
  }
  const next = [...items];
  next[index] = { ...next[index], ...item };
  return next;
}

function mapStatus(status: string | null | undefined): ExecutionItemStatus {
  switch (status) {
    case "running":
      return "running";
    case "failed":
      return "failed";
    case "unavailable":
      return "unavailable";
    case "skipped":
      return "skipped";
    case "success":
    case "complete":
      return "success";
    default:
      return "pending";
  }
}

export function reduceLiveExecutionState(
  state: LiveExecutionState,
  event: AgentRunEvent,
): LiveExecutionState {
  if (state.seenEventIds.has(event.event_id)) {
    return state;
  }
  const seenEventIds = new Set(state.seenEventIds);
  seenEventIds.add(event.event_id);

  const base: LiveExecutionState = {
    ...state,
    runId: event.run_id,
    seenEventIds,
  };

  switch (event.type) {
    case "run_started":
      return {
        ...base,
        isActive: true,
        isComplete: false,
        isFailed: false,
        startedAt: event.timestamp,
      };
    case "node_started": {
      if (!event.node_name) return base;
      return {
        ...base,
        nodes: upsertItem(base.nodes, {
          id: event.node_name,
          kind: "node",
          name: event.node_name,
          label: labelForNode(event.node_name),
          status: "running",
          durationMs: null,
        }),
      };
    }
    case "node_completed":
    case "node_failed": {
      if (!event.node_name) return base;
      return {
        ...base,
        nodes: upsertItem(base.nodes, {
          id: event.node_name,
          kind: "node",
          name: event.node_name,
          label: labelForNode(event.node_name),
          status: mapStatus(event.status),
          durationMs: event.duration_ms ?? null,
          errorMessage:
            typeof event.metadata?.error_message === "string"
              ? event.metadata.error_message
              : undefined,
        }),
      };
    }
    case "tool_started": {
      if (!event.tool_name) return base;
      return {
        ...base,
        parallelActive: true,
        tools: upsertItem(base.tools, {
          id: event.tool_name,
          kind: "tool",
          name: event.tool_name,
          label: labelForTool(event.tool_name),
          status: "running",
          durationMs: null,
        }),
      };
    }
    case "tool_completed": {
      if (!event.tool_name) return base;
      return {
        ...base,
        tools: upsertItem(base.tools, {
          id: event.tool_name,
          kind: "tool",
          name: event.tool_name,
          label: labelForTool(event.tool_name),
          status: mapStatus(event.status),
          durationMs: event.duration_ms ?? null,
          errorMessage:
            typeof event.metadata?.error_message === "string"
              ? event.metadata.error_message
              : undefined,
        }),
      };
    }
    case "parallel_group_started":
      return { ...base, parallelActive: true };
    case "parallel_group_completed":
      return { ...base, parallelActive: false };
    case "run_completed":
      return {
        ...base,
        isActive: false,
        isComplete: true,
        completedAt: event.timestamp,
        totalDurationMs: event.duration_ms ?? null,
        summary: event.metadata ?? {},
      };
    case "run_failed":
      return {
        ...base,
        isActive: false,
        isFailed: true,
        completedAt: event.timestamp,
        totalDurationMs: event.duration_ms ?? null,
        summary: event.metadata ?? {},
      };
    default:
      return base;
  }
}

export function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function countPartialTools(tools: ExecutionItem[]): number {
  return tools.filter((tool) => tool.status === "unavailable").length;
}
