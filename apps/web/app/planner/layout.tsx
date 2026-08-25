import { PlannerShell } from "@/components/planner/planner-shell";
import { PlannerTokenProvider } from "@/lib/planner/auth";

export const dynamic = "force-dynamic";

export default function PlannerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PlannerTokenProvider>
      <PlannerShell>{children}</PlannerShell>
    </PlannerTokenProvider>
  );
}
