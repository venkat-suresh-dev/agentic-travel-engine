"use client";

import type { BudgetSummary } from "@agentic-travel-engine/shared-types";
import { motion, useReducedMotion } from "framer-motion";

import { Badge } from "@/components/ui/badge";
import {
  formatMoney,
  getBudgetHealth,
  type BudgetHealth,
} from "@/lib/planner/format";
import { cn } from "@/lib/utils";

interface BudgetPanelProps {
  budget: BudgetSummary;
  className?: string;
}

const HEALTH_COPY: Record<
  BudgetHealth,
  { label: string; variant: "success" | "warning" | "danger" | "default" }
> = {
  under: { label: "Under budget", variant: "success" },
  near: { label: "Near budget", variant: "warning" },
  exact: { label: "At budget", variant: "default" },
  over: { label: "Over budget", variant: "danger" },
};

export function BudgetPanel({ budget, className }: BudgetPanelProps) {
  const reduceMotion = useReducedMotion();
  const health = getBudgetHealth(budget);
  const healthMeta = HEALTH_COPY[health];
  const spentRatio = Math.min(
    100,
    Math.max(0, (Number(budget.total_cost) / Number(budget.budget_amount)) * 100),
  );

  return (
    <section
      className={cn(
        "rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-soft)]",
        className,
      )}
      aria-labelledby="budget-heading"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
            Budget intelligence
          </p>
          <h2 id="budget-heading" className="mt-2 font-display text-2xl">
            How your budget is tracking
          </h2>
        </div>
        <Badge variant={healthMeta.variant}>{healthMeta.label}</Badge>
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-5">
          <div>
            <p className="text-sm text-[var(--foreground-muted)]">Total trip estimate</p>
            <motion.p
              key={budget.total_cost}
              className="font-display text-4xl text-[var(--foreground)]"
              initial={reduceMotion ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {formatMoney(budget.total_cost, budget.currency)}
            </motion.p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-2xl bg-[var(--surface-elevated)] p-4 ring-1 ring-[var(--border)]">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Budget
              </p>
              <p className="mt-2 text-lg font-medium">
                {formatMoney(budget.budget_amount, budget.currency)}
              </p>
            </div>
            <div className="rounded-2xl bg-[var(--surface-elevated)] p-4 ring-1 ring-[var(--border)]">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Remaining
              </p>
              <p className="mt-2 text-lg font-medium">
                {formatMoney(budget.remaining, budget.currency)}
              </p>
            </div>
          </div>
          <div>
            <div className="mb-2 flex justify-between text-xs text-[var(--foreground-muted)]">
              <span>Budget used</span>
              <span>{spentRatio.toFixed(0)}%</span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-[var(--surface-muted)]"
              role="progressbar"
              aria-valuenow={spentRatio}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Budget utilization"
            >
              <motion.div
                className={cn(
                  "h-full rounded-full",
                  health === "over"
                    ? "bg-[var(--budget-over-fg)]"
                    : health === "near"
                      ? "bg-[var(--budget-near-fg)]"
                      : "bg-[var(--accent)]",
                )}
                initial={reduceMotion ? { width: `${spentRatio}%` } : { width: 0 }}
                animate={{ width: `${spentRatio}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
          </div>
        </div>

        <div className="rounded-2xl bg-[var(--surface-elevated)] p-4 ring-1 ring-[var(--border)]">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
            Where the money goes
          </p>
          <p className="mt-3 text-sm leading-relaxed text-[var(--foreground-secondary)]">
            Category breakdown is derived from the authoritative backend budget
            engine. Totals and remaining balance always come from the server.
          </p>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-[var(--border)] pb-2">
              <dt>Variance</dt>
              <dd>{formatMoney(budget.variance, budget.currency)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>Status</dt>
              <dd>{budget.budget_exceeded ? "Exceeded" : "Within limit"}</dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}
