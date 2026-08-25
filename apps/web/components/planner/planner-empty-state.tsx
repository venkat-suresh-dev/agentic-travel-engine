"use client";

import { ArrowUpRight } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const EXAMPLE_PROMPTS = [
  {
    label: "Dubai · 5 days",
    message:
      "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai.",
  },
  {
    label: "Tokyo · 7 days",
    message: "Plan a relaxed 4-day trip to Tokyo for 2 people in April.",
  },
  {
    label: "Paris · weekend",
    message: "Plan a week in Paris for a couple with a mid-range budget.",
  },
] as const;

const DESTINATIONS = ["Dubai", "Tokyo", "Paris", "Singapore"] as const;

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
  const [message, setMessage] = useState<string>(EXAMPLE_PROMPTS[0]?.message ?? "");
  const labelId = useId();

  return (
    <section
      aria-labelledby="planner-empty-heading"
      data-testid="planner-empty-state"
      className={cn(
        "flex min-h-0 flex-1 flex-col justify-center py-2 sm:py-3 lg:py-2",
        className,
      )}
    >
      <div className="grid items-center gap-4 md:gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] lg:gap-6 xl:gap-8">
        <div className="space-y-3 lg:space-y-4">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--accent)]">
              Plan a trip
            </p>
            <h1
              id="planner-empty-heading"
              className="mt-1 font-display text-[1.625rem] leading-[1.15] tracking-tight text-[var(--foreground)] sm:text-[1.875rem] lg:text-[1.95rem] xl:text-[2.125rem]"
            >
              Plan a trip without the spreadsheet.
            </h1>
            <p className="mt-1.5 max-w-md text-sm leading-snug text-[var(--foreground-secondary)]">
              Describe where you are going and what you want to spend. We return a
              grounded itinerary with live travel data and deterministic budget
              totals.
            </p>
          </div>

          <div
            className="hidden lg:block"
            data-testid="planner-empty-destinations"
          >
            <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
              Popular destinations
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {DESTINATIONS.map((destination) => (
                <button
                  key={destination}
                  type="button"
                  className="rounded-full px-3 py-1 text-sm text-[var(--foreground-secondary)] ring-1 ring-[var(--border)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                  onClick={() =>
                    setMessage(
                      `Plan a 5-day trip to ${destination} for 2 people with a comfortable budget.`,
                    )
                  }
                  disabled={loading}
                >
                  {destination}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] p-3.5 shadow-[var(--shadow-soft)] md:p-4">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
            Start with a request
          </p>
          <div className="mt-1.5 space-y-2">
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
              className="!min-h-[3.75rem] resize-none py-2.5 text-sm leading-snug lg:!min-h-[4rem]"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  if (message.trim() && !loading) {
                    void onSubmit(message.trim());
                  }
                }
              }}
            />

            <div data-testid="planner-empty-examples">
              <p className="text-[11px] text-[var(--foreground-muted)]">Try</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {EXAMPLE_PROMPTS.map((example) => (
                  <button
                    key={example.label}
                    type="button"
                    aria-label={`Use ${example.label} example`}
                    className="rounded-full bg-[var(--surface)] px-2.5 py-1 text-xs text-[var(--foreground-secondary)] ring-1 ring-[var(--border)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                    onClick={() => setMessage(example.message)}
                    disabled={loading}
                  >
                    {example.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-end pt-0.5">
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

          <div
            className="mt-2.5 border-t border-[var(--border)] pt-2.5 lg:hidden"
            data-testid="planner-empty-destinations-mobile"
          >
            <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
              Popular destinations
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {DESTINATIONS.map((destination) => (
                <button
                  key={destination}
                  type="button"
                  className="rounded-full px-3 py-1 text-xs text-[var(--foreground-secondary)] ring-1 ring-[var(--border)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                  onClick={() =>
                    setMessage(
                      `Plan a 5-day trip to ${destination} for 2 people with a comfortable budget.`,
                    )
                  }
                  disabled={loading}
                >
                  {destination}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
