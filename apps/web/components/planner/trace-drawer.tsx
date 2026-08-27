"use client";

import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  MinusCircle,
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
import { formatDuration, type ExecutionItem, type LiveExecutionState } from "@/lib/planner/execution-state";
import {
  buildTraceSummaryChips,
  formatToolTraceDetail,
  groupTraceNodes,
  resolveTraceExecution,
} from "@/lib/planner/tool-trace";
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
    default:
      return <MinusCircle className="h-3.5 w-3.5 text-[var(--foreground-muted)]" />;
  }
}

function TraceRow({ item }: { item: ExecutionItem }) {
  const rightLabel =
    item.kind === "tool"
      ? formatToolTraceDetail(item)
      : item.durationMs !== null
        ? formatDuration(item.durationMs)
        : "—";

  return (
    <li className="flex items-center justify-between gap-3 py-1.5 text-xs">
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
      <span className="shrink-0 font-mono text-right tabular-nums text-[var(--foreground-muted)]">
        {rightLabel}
      </span>
    </li>
  );
}

export function TraceDrawer({ run, execution, isLive = false }: TraceDrawerProps) {
  const resolvedExecution = resolveTraceExecution(run, execution, isLive);

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
  const grouped = groupTraceNodes(nodeItems);
  const chips = buildTraceSummaryChips(run, resolvedExecution);
  const hasTrace =
    nodeItems.length > 0 ||
    toolItems.length > 0 ||
    isLive ||
    Boolean(run.tool_availability?.tools.length) ||
    Boolean(run.critic);
  const triggerLabel = isLive
    ? "Live execution"
    : resolvedExecution.totalDurationMs !== null
      ? `Agent run · ${formatDuration(resolvedExecution.totalDurationMs)}`
      : "Agent run";

  if (!hasTrace) {
    return null;
  }

  const showLegacyUnavailableSection =
    (run.tool_availability?.unavailable_tools.length ?? 0) > 0 &&
    toolItems.length === 0;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 rounded-md px-2.5 font-mono text-[11px] text-[var(--foreground-secondary)] hover:text-[var(--foreground)]"
        >
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent aria-describedby="trace-description">
        <DialogHeader>
          <DialogTitle className="font-display text-xl tracking-tight">
            Agent run
          </DialogTitle>
          <DialogDescription id="trace-description">
            {isLive
              ? "Live execution from the planning agent."
              : resolvedExecution.isFailed
                ? "Planning failed during execution."
                : "How this itinerary was grounded and validated."}
          </DialogDescription>
          {chips.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 font-mono text-[11px] text-[var(--foreground-secondary)]">
              {chips.map((chip) => (
                <span key={chip} className="tabular-nums">
                  {chip}
                </span>
              ))}
            </div>
          ) : null}
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-subtle">
          {grouped.planning.length > 0 ? (
            <section>
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Planning
              </p>
              <ol className="mt-1">
                {grouped.planning.map((item) => (
                  <TraceRow key={item.id} item={item} />
                ))}
              </ol>
            </section>
          ) : null}

          {grouped.knowledge.length > 0 ? (
            <section className="mt-5">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Knowledge
              </p>
              <ol className="mt-1">
                {grouped.knowledge.map((item) => (
                  <TraceRow key={item.id} item={item} />
                ))}
              </ol>
            </section>
          ) : null}

          {toolItems.length > 0 ? (
            <section className="mt-5">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Live data
                {execution.parallelActive ? (
                  <span className="ml-2 text-[var(--accent)]">parallel</span>
                ) : null}
              </p>
              <ol className="mt-1">
                {toolItems.map((item) => (
                  <TraceRow key={item.id} item={item} />
                ))}
              </ol>
            </section>
          ) : null}

          {grouped.validation.length > 0 ? (
            <section className="mt-5">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Validation
              </p>
              <ol className="mt-1">
                {grouped.validation.map((item) => (
                  <TraceRow key={item.id} item={item} />
                ))}
              </ol>
            </section>
          ) : null}

          {showLegacyUnavailableSection ? (
            <section className="mt-5">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Unavailable sources
              </p>
              <ul className="mt-2 space-y-1 text-xs text-[var(--foreground-secondary)]">
                {run.tool_availability?.unavailable_tools.map((tool) => (
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
