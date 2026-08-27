import Link from "next/link";
import { Compass } from "lucide-react";

import { APP_NAME } from "@agentic-travel-engine/shared-types";

const EXAMPLE_PROMPT =
  "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000 from Mumbai.";

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="shrink-0 border-b border-[var(--border)]/60 bg-[var(--background)]/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center justify-between px-4 md:px-6">
          <Link
            href="/"
            className="flex items-center gap-2.5 rounded-full py-1 pr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-foreground)]">
              <Compass className="h-4 w-4" aria-hidden />
            </span>
            <span className="font-display text-[1.15rem] leading-none tracking-tight">
              {APP_NAME}
            </span>
          </Link>
          <Link
            href="/planner"
            className="inline-flex h-9 items-center rounded-full bg-[var(--accent)] px-4 text-sm font-medium text-[var(--accent-foreground)] transition-colors hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          >
            Open planner
          </Link>
        </div>
      </header>
      <main className="relative flex flex-1 flex-col items-center justify-center px-6 py-16 md:py-24">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          aria-hidden
          style={{
            background:
              "radial-gradient(ellipse 70% 45% at 50% 18%, rgba(13, 92, 99, 0.08), transparent 58%)",
          }}
        />
        <div className="relative w-full max-w-xl space-y-8">
          <div className="space-y-4 text-center md:text-left">
            <h1 className="font-display text-[2.5rem] leading-[0.95] tracking-tight text-[var(--foreground)] md:text-[3.25rem]">
              Plan the trip.
              <br />
              <span className="text-[var(--foreground-secondary)]">
                Keep the facts grounded.
              </span>
            </h1>
            <p className="text-base leading-relaxed text-[var(--foreground-secondary)] md:text-lg">
              Describe your trip. We&apos;ll turn it into a plan you can actually
              change.
            </p>
          </div>

          <div className="rounded-xl bg-[var(--surface)]/80 px-4 py-3 text-sm leading-relaxed text-[var(--foreground-muted)]">
            {EXAMPLE_PROMPT}
          </div>

          <div className="flex justify-center md:justify-start">
            <Link
              href="/planner"
              className="inline-flex h-11 items-center rounded-full bg-[var(--accent)] px-6 text-sm font-medium text-[var(--accent-foreground)] transition-colors hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            >
              Start planning
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
