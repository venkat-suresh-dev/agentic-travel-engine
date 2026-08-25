"use client";

import { PlannerShell } from "@/components/planner/planner-shell";
import { PlannerTokenProvider } from "@/lib/planner/auth";

export function PlannerLayoutClient({ children }: { children: React.ReactNode }) {
  return (
    <PlannerTokenProvider>
      <PlannerShell>{children}</PlannerShell>
    </PlannerTokenProvider>
  );
}
