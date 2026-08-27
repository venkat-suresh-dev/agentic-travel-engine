"use client";

import type { BudgetSummary } from "@agentic-travel-engine/shared-types";
import { motion, useReducedMotion } from "framer-motion";

import {
  budgetOverBy,
  budgetSpentPercent,
  formatMoney,
  getBudgetHealth,
  type BudgetHealth,
} from "@/lib/planner/format";
import {
  budgetCategoryLabel,
  budgetExclusionSummary,
  excludedBudgetCategories,
} from "@/lib/planner/logistics";
import type { BudgetRecoveryActions } from "@/lib/planner/suggestions";
import { cn } from "@/lib/utils";

interface BudgetPanelProps {
  budget: BudgetSummary;
  variant?: "full" | "compact" | "inline";
  recovery?: BudgetRecoveryActions | null;
  onApplySuggestion?: (text: string) => void;
  /** Compact over-budget callout without category table (mobile above-fold). */
  mobileRecoveryOnly?: boolean;
  /** Skip headline totals when already shown in trip header. */
  hideSummary?: boolean;
  className?: string;
}

function BudgetBar({
  health,
  spentRatio,
}: {
  health: BudgetHealth;
  spentRatio: number;
}) {
  const reduceMotion = useReducedMotion();
  return (
    <div
      className="relative h-1.5 overflow-hidden rounded-full bg-[var(--surface-muted)]"
      role="progressbar"
      aria-valuenow={Math.round(spentRatio)}
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
  );
}

function CategoryLines({ budget }: { budget: BudgetSummary }) {
  const lines = (budget.categories ?? []).filter(
    (line) => line.included_in_total && line.amount !== null,
  );
  const excluded = excludedBudgetCategories(budget);
  if (lines.length === 0 && excluded.length === 0) {
    return null;
  }
  return (
    <dl className="mt-4 space-y-2">
      {lines.map((line) => (
        <div key={line.category} className="flex items-baseline justify-between gap-3">
          <dt className="text-sm text-[var(--foreground-secondary)]">
            {budgetCategoryLabel(line.category)}
          </dt>
          <dd className="text-sm tabular-nums text-[var(--foreground)]">
            {formatMoney(line.amount ?? 0, line.currency)}
          </dd>
        </div>
      ))}
      {excluded.map((line) => (
        <div
          key={`excluded-${line.category}`}
          className="flex items-baseline justify-between gap-3"
        >
          <dt className="text-sm text-[var(--foreground-secondary)]">
            {budgetCategoryLabel(line.category)}
          </dt>
          <dd className="text-sm text-[var(--foreground-muted)]">Excluded</dd>
        </div>
      ))}
    </dl>
  );
}

function ExclusionNote({ budget }: { budget: BudgetSummary }) {
  const summary = budgetExclusionSummary(budget);
  if (!summary) {
    return null;
  }
  return (
    <p className="mt-2 text-xs leading-snug text-[var(--foreground-muted)]">{summary}</p>
  );
}

function OverBudgetActions({
  recovery,
  onApplySuggestion,
}: {
  recovery: BudgetRecoveryActions;
  onApplySuggestion?: (text: string) => void;
}) {
  return (
    <div className="mt-4 space-y-3">
      <p className="text-sm leading-relaxed text-[var(--foreground-secondary)]">
        {recovery.explanation}
      </p>
      {onApplySuggestion ? (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-foreground)] transition-colors hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            onClick={() => onApplySuggestion(recovery.primary)}
          >
            {recovery.primary}
          </button>
          {recovery.secondary.map((action) => (
            <button
              key={action}
              type="button"
              className="rounded-full border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-secondary)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              onClick={() => onApplySuggestion(action)}
            >
              {action}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function BudgetPanel({
  budget,
  variant = "full",
  recovery = null,
  onApplySuggestion,
  mobileRecoveryOnly = false,
  hideSummary = false,
  className,
}: BudgetPanelProps) {
  const reduceMotion = useReducedMotion();
  const health = getBudgetHealth(budget);
  const spentRatio = budgetSpentPercent(budget);
  const overBy = budgetOverBy(budget);
  const exclusion = budgetExclusionSummary(budget);
  const isOver = health === "over";

  if (mobileRecoveryOnly && isOver && recovery) {
    return (
      <section
        className={cn(
          "rounded-xl bg-[var(--budget-over-bg)]/40 px-4 py-3",
          className,
        )}
        aria-label="Budget recovery"
      >
        <p className="text-sm font-medium text-[var(--budget-over-fg)]">
          Over by {formatMoney(overBy, budget.currency)}
        </p>
        <p className="mt-1 text-sm leading-relaxed text-[var(--foreground-secondary)]">
          {recovery.explanation}
        </p>
        {onApplySuggestion ? (
          <button
            type="button"
            className="mt-2 text-sm font-medium text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            onClick={() => onApplySuggestion(recovery.primary)}
          >
            {recovery.primary} →
          </button>
        ) : null}
      </section>
    );
  }

  if (variant === "inline") {
    return (
      <section
        className={cn("flex items-end justify-between gap-4 py-1", className)}
        aria-label="Budget summary"
      >
        <div className="min-w-0">
          <p className="text-xs text-[var(--foreground-muted)]">Trip budget</p>
          <p className="font-display text-xl leading-none text-[var(--foreground)]">
            {formatMoney(budget.total_cost, budget.currency)}
            <span className="ml-1.5 font-sans text-sm font-normal text-[var(--foreground-muted)]">
              of {formatMoney(budget.budget_amount, budget.currency)}
            </span>
          </p>
          {exclusion ? (
            <p className="mt-1 text-xs text-[var(--foreground-muted)]">{exclusion}</p>
          ) : null}
        </div>
        <p
          className={cn(
            "text-sm tabular-nums",
            isOver
              ? "font-medium text-[var(--budget-over-fg)]"
              : "text-[var(--foreground-secondary)]",
          )}
        >
          {isOver
            ? `Over by ${formatMoney(overBy, budget.currency)}`
            : `${formatMoney(budget.remaining, budget.currency)} remaining`}
        </p>
      </section>
    );
  }

  return (
    <section
      className={cn(className)}
      aria-labelledby={
        variant === "compact" ? "budget-heading-compact" : "budget-heading"
      }
      aria-label={variant === "compact" ? "Budget summary" : undefined}
    >
      <h2
        id={variant === "compact" ? "budget-heading-compact" : "budget-heading"}
        className="text-xs text-[var(--foreground-muted)]"
      >
        Trip budget
      </h2>
      {!hideSummary ? (
        <>
          <motion.p
            key={budget.total_cost}
            className="mt-2 font-display text-[1.75rem] leading-none tabular-nums text-[var(--foreground)]"
            initial={reduceMotion ? false : { opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {formatMoney(budget.total_cost, budget.currency)}
          </motion.p>
          <p className="mt-1 text-sm text-[var(--foreground-secondary)]">
            of {formatMoney(budget.budget_amount, budget.currency)}
          </p>
        </>
      ) : null}

      <div className={hideSummary ? "mt-2" : "mt-3"}>
        <BudgetBar health={health} spentRatio={isOver ? 100 : spentRatio} />
      </div>

      {isOver ? (
        <p className="mt-2 text-sm font-medium tabular-nums text-[var(--budget-over-fg)]">
          Over by {formatMoney(overBy, budget.currency)}
        </p>
      ) : (
        <p className="mt-2 text-sm tabular-nums text-[var(--foreground)]">
          {formatMoney(budget.remaining, budget.currency)} remaining
        </p>
      )}

      {isOver && recovery ? (
        <OverBudgetActions recovery={recovery} onApplySuggestion={onApplySuggestion} />
      ) : null}

      <ExclusionNote budget={budget} />
      {variant !== "compact" || !isOver ? (
        hideSummary ? null : <CategoryLines budget={budget} />
      ) : null}
      {variant === "full" ? (
        <dl className="mt-4 space-y-1 text-xs text-[var(--foreground-muted)]">
          <div className="flex justify-between gap-3">
            <dt>Variance</dt>
            <dd className="tabular-nums font-mono">{formatMoney(budget.variance, budget.currency)}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
