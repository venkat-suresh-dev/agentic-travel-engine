import Link from "next/link";

import { APP_NAME } from "@agentic-travel-engine/shared-types";

interface AuthShellProps {
  children: React.ReactNode;
}

export function AuthShell({ children }: AuthShellProps) {
  return (
    <main className="auth-page flex min-h-screen flex-col items-center justify-center px-4 py-10 sm:py-12">
      <div className="mb-6 w-full max-w-md space-y-2 text-center sm:mb-8">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--foreground-muted)]">
          Grounded travel intelligence
        </p>
        <Link
          href="/"
          className="inline-block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        >
          <h1 className="font-display text-3xl tracking-tight text-[var(--foreground)] sm:text-4xl">
            {APP_NAME}
          </h1>
        </Link>
      </div>
      <div className="auth-clerk-slot mx-auto w-full max-w-[440px]">{children}</div>
    </main>
  );
}
