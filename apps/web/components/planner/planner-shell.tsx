"use client";

import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { Compass } from "lucide-react";

import { APP_NAME } from "@agentic-travel-engine/shared-types";

import { isPlannerAuthEnabled } from "@/lib/planner/auth";
import { cn } from "@/lib/utils";

interface PlannerShellProps {
  children: React.ReactNode;
  className?: string;
}

export function PlannerShell({ children, className }: PlannerShellProps) {
  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)]/80 bg-[var(--background)]/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 md:px-6">
          <Link
            href="/planner"
            className="flex items-center gap-2 rounded-full px-2 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-foreground)]">
              <Compass className="h-4 w-4" aria-hidden />
            </span>
            <span className="font-display text-lg tracking-tight">{APP_NAME}</span>
          </Link>
          {isPlannerAuthEnabled() ? (
            <UserButton afterSignOutUrl="/planner" appearance={{ elements: { avatarBox: "h-9 w-9" } }} />
          ) : (
            <span className="text-xs uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
              Preview
            </span>
          )}
        </div>
      </header>
      <main className={cn("mx-auto max-w-[1440px] px-4 py-6 md:px-6 md:py-8", className)}>
        {children}
      </main>
    </div>
  );
}
