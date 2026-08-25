import { Compass } from "lucide-react";
import Link from "next/link";

import { APP_NAME } from "@agentic-travel-engine/shared-types";

interface AuthShellProps {
  children: React.ReactNode;
  eyebrow: string;
  title: string;
  description: string;
}

export function AuthShell({ children, eyebrow, title, description }: AuthShellProps) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <div className="mb-8 text-center">
        <Link
          href="/planner"
          className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-foreground)]">
            <Compass className="h-4 w-4" aria-hidden />
          </span>
          <span className="font-display text-lg tracking-tight text-[var(--foreground)]">
            {APP_NAME}
          </span>
        </Link>
      </div>
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <p className="text-xs font-medium uppercase tracking-[0.22em] text-[var(--accent)]">
            {eyebrow}
          </p>
          <h1 className="mt-3 font-display text-3xl tracking-tight text-[var(--foreground)]">
            {title}
          </h1>
          <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-[var(--foreground-secondary)]">
            {description}
          </p>
        </div>
        {children}
      </div>
    </main>
  );
}
