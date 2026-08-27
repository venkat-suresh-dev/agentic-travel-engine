"use client";

import { motion, useReducedMotion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle2,
  CircleDashed,
  Loader2,
  MinusCircle,
} from "lucide-react";

import {
  formatDuration,
  type ExecutionItem,
  type LiveExecutionState,
} from "@/lib/planner/execution-state";
import { cn } from "@/lib/utils";

interface LivePlanningStateProps {
  execution: LiveExecutionState;
  mode?: "initial" | "clarification" | "modification";
  className?: string;
}

function StatusIcon({ status }: { status: ExecutionItem["status"] }) {
  switch (status) {
    case "success":
      return (
        <CheckCircle2
          className="h-3.5 w-3.5 shrink-0 text-[var(--accent)]"
          aria-hidden
        />
      );
    case "running":
      return (
        <Loader2
          className="h-3.5 w-3.5 shrink-0 animate-spin text-[var(--accent)]"
          aria-hidden
        />
      );
    case "failed":
      return (
        <AlertCircle
          className="h-3.5 w-3.5 shrink-0 text-[var(--budget-over-fg)]"
          aria-hidden
        />
      );
    case "unavailable":
      return (
        <MinusCircle
          className="h-3.5 w-3.5 shrink-0 text-[var(--foreground-muted)]"
          aria-hidden
        />
      );
    default:
      return (
        <CircleDashed
          className="h-3.5 w-3.5 shrink-0 text-[var(--foreground-muted)]"
          aria-hidden
        />
      );
  }
}

function ExecutionRow({ item }: { item: ExecutionItem }) {
  return (
    <li className="flex items-center justify-between gap-2 text-xs">
      <div className="flex min-w-0 items-center gap-2">
        <StatusIcon status={item.status} />
        <span
          className={cn(
            item.status === "running"
              ? "font-medium text-[var(--foreground)]"
              : item.status === "success"
                ? "text-[var(--foreground-secondary)]"
                : item.status === "unavailable"
                  ? "text-[var(--foreground-muted)]"
                  : "text-[var(--foreground-muted)]",
          )}
        >
          {item.label}
          {item.status === "unavailable" ? " · Unavailable" : null}
        </span>
      </div>
      {item.durationMs !== null ? (
        <span className="shrink-0 tabular-nums text-[var(--foreground-muted)]">
          {formatDuration(item.durationMs)}
        </span>
      ) : null}
    </li>
  );
}

export function LivePlanningState({
  execution,
  mode = "initial",
  className,
}: LivePlanningStateProps) {
  const reduceMotion = useReducedMotion();
  const title =
    mode === "modification"
      ? "Applying your changes"
      : mode === "clarification"
        ? "Updating trip details"
        : "Planning your trip";

  const nodeItems = execution.nodes.filter(
    (node) =>
      ![
        "aggregate_independent_tools",
        "finalize_run",
        "finalize_failure",
        "finalize_modification_failure",
      ].includes(node.name),
  );
  const toolItems = execution.tools;

  return (
    <div
      className={cn("space-y-3", className)}
      role="status"
      aria-live="polite"
      aria-label={title}
    >
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
          {title}
        </p>
      </div>

      {nodeItems.length > 0 ? (
        <motion.ol
          className="space-y-2"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {nodeItems.map((item, index) => (
            <motion.div
              key={item.id}
              initial={reduceMotion ? false : { opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.03 }}
            >
              <ExecutionRow item={item} />
            </motion.div>
          ))}
        </motion.ol>
      ) : null}

      {toolItems.length > 0 ? (
        <div className="space-y-2 rounded-md bg-[var(--surface)]/80 p-2.5">
          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
            Live sources
            {execution.parallelActive ? (
              <span className="ml-1.5 inline-flex items-center gap-1 text-[var(--accent)]">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" />
                parallel
              </span>
            ) : null}
          </p>
          <ol className="space-y-1.5">
            {toolItems.map((item) => (
              <ExecutionRow key={item.id} item={item} />
            ))}
          </ol>
        </div>
      ) : null}

      {nodeItems.length === 0 && toolItems.length === 0 ? (
        <div className="flex items-center gap-2 text-xs text-[var(--foreground-secondary)]">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--accent)]" />
          Starting agent run…
        </div>
      ) : null}
    </div>
  );
}
