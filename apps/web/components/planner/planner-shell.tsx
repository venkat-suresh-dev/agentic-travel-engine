"use client";

import Link from "next/link";
import { Compass } from "lucide-react";
import type { ReactNode } from "react";

import { APP_NAME } from "@agentic-travel-engine/shared-types";

import { AccountControl } from "@/components/planner/account-control";
import { isPlannerAuthEnabled } from "@/lib/planner/auth";
import { cn } from "@/lib/utils";

interface PlannerShellProps {
  children: ReactNode;
  className?: string;
}

export function PlannerShell({ children, className }: PlannerShellProps) {
  return (
    <div className="flex min-h-dvh flex-col bg-[var(--background)] text-[var(--foreground)]">
      <header className="sticky top-0 z-40 shrink-0 border-b border-[var(--border)]/80 bg-[var(--background)]/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center justify-between px-4 md:px-6">
          <Link
            href="/planner"
            className="flex items-center gap-2.5 rounded-full py-1 pr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-foreground)]">
              <Compass className="h-4 w-4" aria-hidden />
            </span>
            <span className="font-display text-[1.15rem] leading-none tracking-tight">
              {APP_NAME}
            </span>
          </Link>
          {isPlannerAuthEnabled() ? (
            <AccountControl />
          ) : (
            <span className="text-[10px] uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
              Preview
            </span>
          )}
        </div>
      </header>
      <main
        className={cn(
          "mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col px-4 py-3 md:px-6",
          className,
        )}
      >
        {children}
      </main>
    </div>
  );
}
