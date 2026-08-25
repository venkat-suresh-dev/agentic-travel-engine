"use client";

import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import {
  AlertCircle,
  CheckCircle2,
  GitBranch,
  Layers,
  Loader2,
  MinusCircle,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  countPartialTools,
  formatDuration,
  type ExecutionItem,
  type LiveExecutionState,
} from "@/lib/planner/execution-state";
import { cn } from "@/lib/utils";

interface TraceDrawerProps {
  run: AgentRunResponse;
  execution: LiveExecutionState;
  isLive?: boolean;
}

function TraceStatusIcon({ status }: { status: ExecutionItem["status"] }) {
  switch (status) {
    case "success":
      return <CheckCircle2 className="h-3.5 w-3.5 text-[var(--accent)]" />;
    case "running":
      return <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--accent)]" />;
    case "failed":
      return <AlertCircle className="h-3.5 w-3.5 text-[var(--budget-over-fg)]" />;
    case "unavailable":
      return <MinusCircle className="h-3.5 w-3.5 text-[var(--foreground-muted)]" />;
    default:
      return <MinusCircle className="h-3.5 w-3.5 text-[var(--foreground-muted)]" />;
  }
}

function TraceRow({ item }: { item: ExecutionItem }) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-xs hover:bg-[var(--surface-hover)]">
      <div className="flex min-w-0 items-center gap-2">
        <TraceStatusIcon status={item.status} />
        <span
          className={cn(
            item.status === "running"
              ? "font-medium text-[var(--foreground)]"
              : "text-[var(--foreground-secondary)]",
          )}
        >
          {item.label}
        </span>
      </div>
      <span className="shrink-0 tabular-nums text-[var(--foreground-muted)]">
        {item.status === "unavailable"
          ? "Unavailable"
          : formatDuration(item.durationMs)}
      </span>
    </li>
  );
}

function buildSummaryChips(
  run: AgentRunResponse,
  execution: LiveExecutionState,
): string[] {
  const chips: string[] = [];
  if (execution.totalDurationMs !== null) {
    chips.push(formatDuration(execution.totalDurationMs));
  }
  if (execution.tools.length > 0) {
    chips.push(`${execution.tools.length} tools`);
  }
  const partial = countPartialTools(execution.tools);
  if (partial > 0) {
    chips.push(`${partial} partial source${partial === 1 ? "" : "s"}`);
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

export function TraceDrawer({ run, execution, isLive = false }: TraceDrawerProps) {
  const hasLiveTrace =
    execution.nodes.length > 0 || execution.tools.length > 0 || isLive;
  const fallbackTools = (run.tool_availability?.unavailable_tools ?? []).map(
    (tool) => ({
      id: tool,
      kind: "tool" as const,
      name: tool,
      label: tool,
      status: "unavailable" as const,
      durationMs: null,
    }),
  );
  const resolvedExecution: LiveExecutionState = hasLiveTrace
    ? execution
    : { ...execution, tools: fallbackTools, isComplete: true };

  const nodeItems = resolvedExecution.nodes.filter(
    (node) =>
      ![
        "aggregate_independent_tools",
        "finalize_run",
        "finalize_failure",
        "finalize_modification_failure",
      ].includes(node.name),
  );
  const toolItems = resolvedExecution.tools;
  const chips = buildSummaryChips(run, resolvedExecution);
  const hasTrace =
    nodeItems.length > 0 ||
    toolItems.length > 0 ||
    isLive ||
    Boolean(run.tool_availability) ||
    Boolean(run.critic);
  const triggerLabel = isLive
    ? "Live execution"
    : resolvedExecution.totalDurationMs !== null
      ? `Agent run · ${formatDuration(resolvedExecution.totalDurationMs)}`
      : "View execution";

  if (!hasTrace) {
    return null;
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="secondary" size="sm" className="h-8 rounded-lg px-3 text-xs">
          <GitBranch className="h-3.5 w-3.5" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent aria-describedby="trace-description">
        <DialogHeader>
          <DialogTitle>Agent run</DialogTitle>
          <DialogDescription id="trace-description">
            {isLive
              ? "Live execution trace from the planning agent."
              : resolvedExecution.isFailed
                ? "Planning failed during execution."
                : "Execution trace from the planning agent."}
          </DialogDescription>
          {chips.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {chips.map((chip) => (
                <span
                  key={chip}
                  className="rounded-full bg-[var(--surface-elevated)] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--foreground-secondary)] ring-1 ring-[var(--border)]"
                >
                  {chip}
                </span>
              ))}
            </div>
          ) : null}
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-thin">
          {nodeItems.length > 0 ? (
            <section className="space-y-2">
              <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                <Layers className="h-3 w-3" />
                Nodes
              </div>
              <ol className="space-y-0.5">
                {nodeItems.map((item) => (
                  <TraceRow key={item.id} item={item} />
                ))}
              </ol>
            </section>
          ) : null}

          {toolItems.length > 0 ? (
            <section className="mt-5 space-y-2">
              <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                <Wrench className="h-3 w-3" />
                Parallel tools
              </div>
              <ol className="space-y-0.5">
                {toolItems.map((item) => (
                  <TraceRow key={item.id} item={item} />
                ))}
              </ol>
            </section>
          ) : null}

          {run.tool_availability?.unavailable_tools.length ? (
            <section className="mt-5 rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)]/60 p-3">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Unavailable sources
              </p>
              <ul className="mt-2 space-y-1 text-xs text-[var(--foreground-secondary)]">
                {run.tool_availability.unavailable_tools.map((tool) => (
                  <li key={tool}>{tool}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {run.critic && (run.critic.issues.length > 0 || run.critic.warnings.length > 0) ? (
            <section className="mt-5 space-y-2">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Critic notes
              </p>
              {run.critic.issues.map((issue) => (
                <p key={issue} className="text-xs text-[var(--budget-over-fg)]">
                  {issue}
                </p>
              ))}
              {run.critic.warnings.map((warning) => (
                <p key={warning} className="text-xs text-[var(--foreground-secondary)]">
                  {warning}
                </p>
              ))}
            </section>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
