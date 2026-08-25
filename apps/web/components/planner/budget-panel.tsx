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
  variant?: "full" | "compact" | "inline";
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

function BudgetProgress({
  budget,
  health,
  spentRatio,
  className,
}: {
  budget: BudgetSummary;
  health: BudgetHealth;
  spentRatio: number;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div className={className}>
      <div className="mb-1.5 flex justify-between text-[11px] text-[var(--foreground-muted)]">
        <span>Budget used</span>
        <span>{spentRatio.toFixed(0)}%</span>
      </div>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-[var(--surface-muted)]"
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
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <div className="flex justify-between gap-2">
          <dt className="text-[var(--foreground-muted)]">Variance</dt>
          <dd className="font-medium">{formatMoney(budget.variance, budget.currency)}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-[var(--foreground-muted)]">Status</dt>
          <dd className="font-medium">
            {budget.budget_exceeded ? "Exceeded" : "Within limit"}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function BudgetPanel({
  budget,
  variant = "full",
  className,
}: BudgetPanelProps) {
  const reduceMotion = useReducedMotion();
  const health = getBudgetHealth(budget);
  const healthMeta = HEALTH_COPY[health];
  const spentRatio = Math.min(
    100,
    Math.max(0, (Number(budget.total_cost) / Number(budget.budget_amount)) * 100),
  );

  if (variant === "inline") {
    return (
      <section
        className={cn(
          "flex items-center justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3",
          className,
        )}
        aria-label="Budget summary"
      >
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
            Trip estimate
          </p>
          <p className="font-display text-xl text-[var(--foreground)]">
            {formatMoney(budget.total_cost, budget.currency)}
            <span className="ml-1.5 text-sm font-normal text-[var(--foreground-muted)]">
              / {formatMoney(budget.budget_amount, budget.currency)}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-sm font-medium text-[var(--foreground-secondary)]">
            {formatMoney(budget.remaining, budget.currency)} left
          </p>
          <Badge variant={healthMeta.variant}>{healthMeta.label}</Badge>
        </div>
      </section>
    );
  }

  if (variant === "compact") {
    return (
      <section
        className={cn(
          "rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4",
          className,
        )}
        aria-labelledby="budget-heading-compact"
      >
        <div className="flex items-start justify-between gap-2">
          <p
            id="budget-heading-compact"
            className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]"
          >
            Budget
          </p>
          <Badge variant={healthMeta.variant}>{healthMeta.label}</Badge>
        </div>
        <motion.p
          key={budget.total_cost}
          className="mt-2 font-display text-3xl leading-none text-[var(--foreground)]"
          initial={reduceMotion ? false : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {formatMoney(budget.total_cost, budget.currency)}
        </motion.p>
        <p className="mt-1 text-xs text-[var(--foreground-secondary)]">
          of {formatMoney(budget.budget_amount, budget.currency)} ·{" "}
          {formatMoney(budget.remaining, budget.currency)} remaining
        </p>
        <BudgetProgress
          budget={budget}
          health={health}
          spentRatio={spentRatio}
          className="mt-4"
        />
      </section>
    );
  }

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

      <div className="mt-6 grid gap-6 md:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4">
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
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-[var(--surface-elevated)] p-3 ring-1 ring-[var(--border)]">
              <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Budget
              </p>
              <p className="mt-1 text-lg font-medium">
                {formatMoney(budget.budget_amount, budget.currency)}
              </p>
            </div>
            <div className="rounded-xl bg-[var(--surface-elevated)] p-3 ring-1 ring-[var(--border)]">
              <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                Remaining
              </p>
              <p className="mt-1 text-lg font-medium">
                {formatMoney(budget.remaining, budget.currency)}
              </p>
            </div>
          </div>
          <BudgetProgress budget={budget} health={health} spentRatio={spentRatio} />
        </div>

        <div className="rounded-xl bg-[var(--surface-elevated)] p-4 ring-1 ring-[var(--border)]">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
            Authoritative totals
          </p>
          <p className="mt-2 text-sm leading-relaxed text-[var(--foreground-secondary)]">
            Budget figures come from the backend engine. The frontend never
            recomputes totals.
          </p>
        </div>
      </div>
    </section>
  );
}
