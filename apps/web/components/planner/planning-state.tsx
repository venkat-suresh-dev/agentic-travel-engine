"use client";

import { motion, useReducedMotion } from "framer-motion";
import { CheckCircle2, CircleDashed, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export type PlanningPhase =
  | "understanding"
  | "searching"
  | "weather"
  | "building"
  | "budget"
  | "validating";

const PHASES: Array<{ id: PlanningPhase; label: string }> = [
  { id: "understanding", label: "Understanding your preferences" },
  { id: "searching", label: "Finding the best options" },
  { id: "weather", label: "Checking weather" },
  { id: "building", label: "Building the itinerary" },
  { id: "budget", label: "Checking the budget" },
  { id: "validating", label: "Validating the plan" },
];

interface PlanningStateProps {
  activePhase: PlanningPhase;
  mode?: "initial" | "clarification" | "modification";
  className?: string;
}

export function PlanningState({
  activePhase,
  mode = "initial",
  className,
}: PlanningStateProps) {
  const reduceMotion = useReducedMotion();
  const activeIndex = PHASES.findIndex((phase) => phase.id === activePhase);
  const title =
    mode === "modification"
      ? "Applying your changes"
      : mode === "clarification"
        ? "Updating your trip details"
        : "Planning your trip";

  return (
    <div
      className={cn(
        "rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-soft)]",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-label={title}
    >
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
        In progress
      </p>
      <h3 className="mt-2 font-display text-2xl text-[var(--foreground)]">{title}</h3>
      <ol className="mt-6 space-y-3">
        {PHASES.map((phase, index) => {
          const isComplete = index < activeIndex;
          const isActive = index === activeIndex;
          return (
            <motion.li
              key={phase.id}
              className="flex items-center gap-3 text-sm"
              initial={reduceMotion ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              {isComplete ? (
                <CheckCircle2
                  className="h-4 w-4 text-[var(--accent)]"
                  aria-hidden
                />
              ) : isActive ? (
                <Loader2
                  className="h-4 w-4 animate-spin text-[var(--accent)]"
                  aria-hidden
                />
              ) : (
                <CircleDashed
                  className="h-4 w-4 text-[var(--foreground-muted)]"
                  aria-hidden
                />
              )}
              <span
                className={cn(
                  isActive
                    ? "font-medium text-[var(--foreground)]"
                    : isComplete
                      ? "text-[var(--foreground-secondary)]"
                      : "text-[var(--foreground-muted)]",
                )}
              >
                {phase.label}
              </span>
            </motion.li>
          );
        })}
      </ol>
    </div>
  );
}
