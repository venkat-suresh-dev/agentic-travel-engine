import Link from "next/link";

import { APP_NAME } from "@agentic-travel-engine/shared-types";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-2xl space-y-6 text-center">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--foreground-muted)]">
          Grounded travel intelligence
        </p>
        <h1 className="font-display text-5xl tracking-tight text-[var(--foreground)]">
          {APP_NAME}
        </h1>
        <p className="text-lg leading-relaxed text-[var(--foreground-secondary)]">
          Plan trips with real travel data, deterministic budgets, and
          conversational modifications.
        </p>
        <Link
          href="/planner"
          className="inline-flex h-12 items-center justify-center rounded-full bg-[var(--accent)] px-6 text-sm font-medium text-[var(--accent-foreground)] transition-colors hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        >
          Open planner
        </Link>
      </div>
    </main>
  );
}
