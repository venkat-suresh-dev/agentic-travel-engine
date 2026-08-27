import type { AgentRunResponse, ToolExecutionRecord } from "@agentic-travel-engine/shared-types";
import { TOOL_LABELS, TOOL_NODE_LABELS } from "@agentic-travel-engine/shared-types";

import { DATA_KIND_LABELS } from "@/lib/planner/format";
import {
  type ExecutionItem,
  type ExecutionItemStatus,
  type LiveExecutionState,
} from "@/lib/planner/execution-state";

function labelForToolName(toolName: string): string {
  return (
    TOOL_NODE_LABELS[toolName] ??
    TOOL_LABELS[toolName] ??
    toolName.replaceAll("_", " ")
  );
}

function mapRecordStatus(status: ToolExecutionRecord["status"]): ExecutionItemStatus {
  switch (status) {
    case "success":
      return "success";
    case "unavailable":
      return "unavailable";
    case "error":
      return "failed";
    case "skipped":
      return "skipped";
    default:
      return "pending";
  }
}

export function toolRecordsToExecutionItems(
  records: ToolExecutionRecord[],
): ExecutionItem[] {
  return records.map((record) => ({
    id: record.tool_name,
    kind: "tool" as const,
    name: record.tool_name,
    label: labelForToolName(record.tool_name),
    status: mapRecordStatus(record.status),
    durationMs: record.duration_ms,
    dataMode: record.data_mode,
    provider: record.provider,
  }));
}

export function formatToolTraceDetail(item: ExecutionItem): string {
  if (item.status === "unavailable") {
    return "Unavailable";
  }
  if (item.status === "failed") {
    return "Failed";
  }
  if (item.status === "skipped") {
    return "Skipped";
  }

  const provider = shortenProvider(item.provider);
  if (item.dataMode === "sandbox") {
    return `Sandbox · ${provider}`;
  }
  if (item.dataMode && item.dataMode in DATA_KIND_LABELS) {
    const kind = DATA_KIND_LABELS[item.dataMode as keyof typeof DATA_KIND_LABELS];
    return `${kind.label} · ${provider}`;
  }
  return provider;
}

function shortenProvider(provider: string | null | undefined): string {
  if (!provider) {
    return "provider";
  }
  return provider
    .replace(/-google-flights$/i, "")
    .replace(/-sandbox$/i, "")
    .replaceAll("-", " ");
}

export function resolveTraceExecution(
  run: AgentRunResponse,
  execution: LiveExecutionState,
  isLive: boolean,
): LiveExecutionState {
  const apiTools = run.tool_availability?.tools ?? [];
  const hasAuthoritativeTools = apiTools.length > 0;
  const shouldPreferApiTools =
    hasAuthoritativeTools &&
    !isLive &&
    (execution.isComplete || run.status === "complete");

  if (shouldPreferApiTools) {
    return {
      ...execution,
      tools: toolRecordsToExecutionItems(apiTools),
      totalDurationMs:
        run.tool_availability?.duration_ms ?? execution.totalDurationMs,
      isComplete: true,
    };
  }

  if (execution.tools.length > 0 || execution.nodes.length > 0 || isLive) {
    return execution;
  }

  if (hasAuthoritativeTools) {
    return {
      ...execution,
      tools: toolRecordsToExecutionItems(apiTools),
      totalDurationMs: run.tool_availability?.duration_ms ?? null,
      isComplete: true,
    };
  }

  return execution;
}

export function countUnavailableTools(tools: ExecutionItem[]): number {
  return tools.filter(
    (tool) => tool.status === "unavailable" || tool.status === "failed",
  ).length;
}

export function buildTraceSummaryChips(
  run: AgentRunResponse,
  execution: LiveExecutionState,
): string[] {
  const chips: string[] = [];
  if (execution.totalDurationMs !== null) {
    chips.push(formatTraceDuration(execution.totalDurationMs));
  }
  if (execution.tools.length > 0) {
    chips.push(`${execution.tools.length} tools`);
  }

  const unavailable = countUnavailableTools(execution.tools);
  const successful = execution.tools.length - unavailable;
  if (unavailable > 0) {
    chips.push(
      `${unavailable} unavailable source${unavailable === 1 ? "" : "s"}`,
    );
    if (run.tool_availability?.aggregate_status === "partial") {
      chips.push("status partial");
    }
  } else if (successful > 0) {
    chips.push(`${successful} source${successful === 1 ? "" : "s"}`);
  }

  if (run.critic?.valid) {
    chips.push("Critic passed");
  } else if (run.critic && !run.critic.valid) {
    chips.push("Critic issues");
  }
  if (run.budget && !run.budget.budget_exceeded) {
    chips.push("Budget validated");
  }
  return chips;
}

function formatTraceDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

export function groupTraceNodes(nodes: ExecutionItem[]): {
  planning: ExecutionItem[];
  knowledge: ExecutionItem[];
  validation: ExecutionItem[];
} {
  const knowledgeNames = new Set(["retrieve_context"]);
  const validationNames = new Set([
    "critic_validate",
    "compute_budget",
    "recompute_modification_budget",
    "convert_currency",
  ]);
  const planning: ExecutionItem[] = [];
  const knowledge: ExecutionItem[] = [];
  const validation: ExecutionItem[] = [];
  for (const node of nodes) {
    if (knowledgeNames.has(node.name)) {
      knowledge.push(node);
    } else if (validationNames.has(node.name)) {
      validation.push(node);
    } else {
      planning.push(node);
    }
  }
  return { planning, knowledge, validation };
}
