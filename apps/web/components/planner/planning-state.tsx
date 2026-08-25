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
  { id: "understanding", label: "Understanding trip requirements" },
  { id: "searching", label: "Searching travel options" },
  { id: "weather", label: "Checking conditions" },
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
        ? "Updating trip details"
        : "Plan in progress";

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
      <ol className="space-y-2">
        {PHASES.map((phase, index) => {
          const isComplete = index < activeIndex;
          const isActive = index === activeIndex;
          return (
            <motion.li
              key={phase.id}
              className="flex items-center gap-2 text-xs"
              initial={reduceMotion ? false : { opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.04 }}
            >
              {isComplete ? (
                <CheckCircle2
                  className="h-3.5 w-3.5 text-[var(--accent)]"
                  aria-hidden
                />
              ) : isActive ? (
                <Loader2
                  className="h-3.5 w-3.5 animate-spin text-[var(--accent)]"
                  aria-hidden
                />
              ) : (
                <CircleDashed
                  className="h-3.5 w-3.5 text-[var(--foreground-muted)]"
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
