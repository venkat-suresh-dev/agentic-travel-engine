"use client";

import { ArrowUpRight } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const EXAMPLE_PROMPT = {
  label: "Dubai · 5 days",
  message:
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000 from Mumbai.",
} as const;

interface PlannerEmptyStateProps {
  loading?: boolean;
  onSubmit: (message: string) => Promise<void> | void;
  className?: string;
}

export function PlannerEmptyState({
  loading = false,
  onSubmit,
  className,
}: PlannerEmptyStateProps) {
  const [message, setMessage] = useState<string>(EXAMPLE_PROMPT.message);
  const labelId = useId();

  return (
    <section
      aria-labelledby="planner-empty-heading"
      data-testid="planner-empty-state"
      className={cn(
        "flex min-h-0 flex-1 flex-col justify-center py-4 sm:py-8",
        className,
      )}
    >
      <div className="mx-auto w-full max-w-xl">
        <h1
          id="planner-empty-heading"
          className="font-display text-[2rem] leading-[1.1] tracking-tight text-[var(--foreground)] sm:text-[2.25rem]"
        >
          Describe your trip.
        </h1>
        <p className="mt-3 text-base leading-relaxed text-[var(--foreground-secondary)]">
          We&apos;ll turn it into a plan you can actually change — with live flights,
          stays, and a day-by-day itinerary grounded in real data.
        </p>

        <div className="mt-8">
          <label id={labelId} className="sr-only" htmlFor="planner-empty-input">
            Trip planning request
          </label>
          <Textarea
            id="planner-empty-input"
            data-testid="planner-empty-composer"
            aria-labelledby={labelId}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            disabled={loading}
            rows={3}
            className="!min-h-[4.5rem] resize-none rounded-xl py-3 text-sm leading-snug"
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (message.trim() && !loading) {
                  void onSubmit(message.trim());
                }
              }
            }}
          />

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div data-testid="planner-empty-examples">
              <button
                type="button"
                aria-label={`Use ${EXAMPLE_PROMPT.label} example`}
                className="text-sm text-[var(--foreground-secondary)] underline-offset-4 hover:text-[var(--foreground)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                onClick={() => setMessage(EXAMPLE_PROMPT.message)}
                disabled={loading}
              >
                Try {EXAMPLE_PROMPT.label}
              </button>
            </div>
            <Button
              data-testid="planner-empty-cta"
              disabled={loading || !message.trim()}
              onClick={() => void onSubmit(message.trim())}
            >
              Plan this trip
              <ArrowUpRight className="h-4 w-4" aria-hidden />
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
