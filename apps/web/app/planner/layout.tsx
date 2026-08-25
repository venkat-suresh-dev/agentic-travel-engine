import { PlannerLayoutClient } from "@/app/planner/planner-layout-client";
import { requirePlannerAuth } from "@/lib/planner/require-auth";

export const dynamic = "force-dynamic";

export default async function PlannerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requirePlannerAuth();

  return <PlannerLayoutClient>{children}</PlannerLayoutClient>;
}
