"use client";

import { ArrowUpRight } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const STARTERS = [
  "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai.",
  "Plan a relaxed 4-day trip to Tokyo for 2 people in April.",
  "Plan a week in Paris for a couple with a mid-range budget.",
];

const DESTINATIONS = ["Dubai", "Tokyo", "Paris", "Singapore"];

interface PlannerEmptyStateProps {
  loading?: boolean;
  onSubmit: (message: string) => Promise<void> | void;
}

export function PlannerEmptyState({ loading = false, onSubmit }: PlannerEmptyStateProps) {
  const [message, setMessage] = useState(STARTERS[0] ?? "");
  const labelId = useId();

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-4xl flex-col justify-center px-4 py-12">
      <div className="relative overflow-hidden rounded-[2.5rem] border border-[var(--border)] bg-[var(--surface-elevated)] px-6 py-10 shadow-[var(--shadow-elevated)] md:px-10 md:py-14">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(13,92,99,0.07),transparent_52%)]"
          aria-hidden
        />
        <div className="relative">
        <p className="text-xs font-medium uppercase tracking-[0.22em] text-[var(--accent)]">
          AI Trip Planner
        </p>
        <h1 className="mt-4 max-w-2xl font-display text-4xl leading-tight text-[var(--foreground)] md:text-6xl">
          Plan a trip without starting from a spreadsheet.
        </h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-[var(--foreground-secondary)]">
          Tell us where you are going, when you are traveling, and what you want
          to spend. We will build a grounded itinerary with real travel data and
          deterministic budget intelligence.
        </p>

        <div className="mt-8 space-y-3">
          <label id={labelId} className="sr-only" htmlFor="planner-empty-input">
            Trip planning request
          </label>
          <Textarea
            id="planner-empty-input"
            aria-labelledby={labelId}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            disabled={loading}
            className="min-h-[140px] text-base"
          />
          <div className="flex flex-wrap gap-2">
            {STARTERS.map((starter, index) => (
              <button
                key={starter}
                type="button"
                aria-label={`Use example trip ${index + 1}`}
                className="rounded-full bg-[var(--surface)] px-3 py-1.5 text-left text-xs text-[var(--foreground-secondary)] ring-1 ring-[var(--border)] transition-colors hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                onClick={() => setMessage(starter)}
                disabled={loading}
              >
                Example {index + 1}
              </button>
            ))}
          </div>
          <div className="flex justify-end">
            <Button
              size="lg"
              disabled={loading || !message.trim()}
              onClick={() => void onSubmit(message.trim())}
            >
              Plan this trip
              <ArrowUpRight className="h-4 w-4" aria-hidden />
            </Button>
          </div>
        </div>

        <div className="mt-10 border-t border-[var(--border)] pt-6">
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
            Popular starting points
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {DESTINATIONS.map((destination) => (
              <button
                key={destination}
                type="button"
                className="rounded-full px-4 py-2 text-sm text-[var(--foreground)] ring-1 ring-[var(--border)] transition-colors hover:bg-[var(--surface-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
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
    </div>
  );
}
