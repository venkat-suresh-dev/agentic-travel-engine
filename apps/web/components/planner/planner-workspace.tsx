"use client";

import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";

import { BudgetPanel } from "@/components/planner/budget-panel";
import { ConversationPanel } from "@/components/planner/conversation-panel";
import { FailureBanner } from "@/components/planner/failure-banner";
import { ItineraryTimeline } from "@/components/planner/itinerary-timeline";
import { ModificationSummary } from "@/components/planner/modification-summary";
import {
  PlanningState,
  type PlanningPhase,
} from "@/components/planner/planning-state";
import { PlannerComposer } from "@/components/planner/planner-composer";
import { TripHeader } from "@/components/planner/trip-header";
import type { PlannerSession } from "@/lib/planner/storage";

interface PlannerWorkspaceProps {
  session: PlannerSession | null;
  isMutating?: boolean;
  planningPhase?: PlanningPhase;
  planningMode?: "initial" | "clarification" | "modification";
  onSendMessage: (message: string) => Promise<void>;
}

const MODIFICATION_SUGGESTIONS = [
  "Make day 2 more relaxed",
  "Find a cheaper dinner on day 3",
  "Change the hotel",
  "Make the trip more budget friendly",
];

function clarificationPrompt(run: AgentRunResponse): string {
  if (run.clarification?.message) {
    return run.clarification.message;
  }
  if (run.missing_fields.length > 0) {
    return `Still needed: ${run.missing_fields.join(", ")}`;
  }
  return "Add the missing trip details to continue.";
}

export function PlannerWorkspace({
  session,
  isMutating = false,
  planningPhase = "building",
  planningMode = "initial",
  onSendMessage,
}: PlannerWorkspaceProps) {
  const run = session?.run;
  const history = session?.history ?? [];
  const hasItinerary = Boolean(run?.itinerary);
  const isClarifying = run?.status === "needs_clarification";
  const modificationFailed =
    run?.status === "failed" && run.modification_failure?.preserved_itinerary;

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div className="space-y-4 xl:sticky xl:top-24 xl:self-start">
        <ConversationPanel history={history} className="min-h-[420px]" />
        <div className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-soft)]">
          {isMutating ? (
            <PlanningState activePhase={planningPhase} mode={planningMode} />
          ) : (
            <>
              {isClarifying && run ? (
                <p className="mb-4 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                  {clarificationPrompt(run)}
                </p>
              ) : hasItinerary ? (
                <p className="mb-4 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                  What would you like to change?
                </p>
              ) : null}
              <PlannerComposer
                loading={isMutating}
                disabled={!run}
                placeholder={
                  hasItinerary
                    ? "Describe a change to your itinerary…"
                    : "Add the missing details or refine your request…"
                }
                submitLabel={hasItinerary ? "Apply change" : "Continue planning"}
                suggestions={hasItinerary ? MODIFICATION_SUGGESTIONS : []}
                onSubmit={onSendMessage}
              />
            </>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {run ? <TripHeader run={run} /> : null}

        {modificationFailed ? (
          <FailureBanner
            title="We couldn't apply that change"
            message={run?.error ?? run?.modification_failure?.message ?? ""}
            preserved
          />
        ) : null}

        {run?.planning_failure ? (
          <FailureBanner
            title="Planning could not be completed"
            message={run.planning_failure.message}
          />
        ) : null}

        {run?.operation.operation_type === "modification" ? (
          <ModificationSummary run={run} />
        ) : null}

        {run?.budget ? <BudgetPanel budget={run.budget} /> : null}

        {run?.itinerary ? (
          <ItineraryTimeline
            itinerary={run.itinerary}
            affectedDays={run.operation.affected_days}
          />
        ) : !isMutating && run?.status === "needs_clarification" ? (
          <div className="rounded-[2rem] border border-dashed border-[var(--border)] bg-[var(--surface)] px-6 py-12 text-center">
            <p className="font-display text-2xl text-[var(--foreground)]">
              Almost there
            </p>
            <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-[var(--foreground-secondary)]">
              Once the missing details are provided, we will search live travel
              data and compose your itinerary here.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
