"use client";

import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import { useState } from "react";

import { BudgetPanel } from "@/components/planner/budget-panel";
import { ConversationPanel } from "@/components/planner/conversation-panel";
import { FailureBanner } from "@/components/planner/failure-banner";
import { ItineraryMap } from "@/components/planner/itinerary-map";
import { ItineraryTimeline } from "@/components/planner/itinerary-timeline";
import { LivePlanningState } from "@/components/planner/live-planning-state";
import { ModificationSummary } from "@/components/planner/modification-summary";
import { PlannerComposer } from "@/components/planner/planner-composer";
import { TraceDrawer } from "@/components/planner/trace-drawer";
import { TripHeader } from "@/components/planner/trip-header";
import type { LiveExecutionState } from "@/lib/planner/execution-state";
import type { PlannerSession } from "@/lib/planner/storage";

interface PlannerWorkspaceProps {
  session: PlannerSession | null;
  isMutating?: boolean;
  planningMode?: "initial" | "clarification" | "modification";
  execution?: LiveExecutionState;
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
  planningMode = "initial",
  execution,
  onSendMessage,
}: PlannerWorkspaceProps) {
  const run = session?.run;
  const history = session?.history ?? [];
  const hasItinerary = Boolean(run?.itinerary);
  const isClarifying = run?.status === "needs_clarification";
  const modificationFailed =
    run?.status === "failed" && run.modification_failure?.preserved_itinerary;
  const liveExecution = execution;
  const [selectedDay, setSelectedDay] = useState(
    run?.itinerary?.days[0]?.day_number ?? 1,
  );
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [mapCollapsed, setMapCollapsed] = useState(true);

  if (!run) {
    return null;
  }

  if (!hasItinerary && !isMutating) {
    return (
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start">
        <div className="space-y-3">
          <TripHeader run={run} />
          {run.planning_failure ? (
            <FailureBanner
              title="Planning could not be completed"
              message={run.planning_failure.message}
            />
          ) : null}
          <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface)] px-5 py-8 text-center">
            <p className="font-display text-xl text-[var(--foreground)]">Almost there</p>
            <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-[var(--foreground-secondary)]">
              Once the missing details are provided, we will search live travel data
              and compose your itinerary here.
            </p>
          </div>
        </div>
        <aside className="space-y-3">
          <ConversationPanel history={history} />
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
            {isClarifying ? (
              <p className="mb-3 text-xs leading-relaxed text-[var(--foreground-secondary)]">
                {clarificationPrompt(run)}
              </p>
            ) : null}
            <PlannerComposer
              loading={isMutating}
              disabled={!run}
              placeholder="Add the missing details or refine your request…"
              submitLabel="Continue planning"
              onSubmit={onSendMessage}
            />
          </div>
        </aside>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <TripHeader run={run} />
        </div>
        {liveExecution ? (
          <TraceDrawer
            run={run}
            execution={liveExecution}
            isLive={isMutating || liveExecution.isActive}
          />
        ) : run.tool_availability || run.critic ? (
          <TraceDrawer
            run={run}
            execution={{
              runId: run.run_id,
              isActive: false,
              isComplete: true,
              isFailed: false,
              startedAt: null,
              completedAt: null,
              totalDurationMs: null,
              nodes: [],
              tools: [],
              parallelActive: false,
              seenEventIds: new Set(),
              summary: {},
            }}
          />
        ) : null}
      </div>

      {run.budget ? (
        <BudgetPanel budget={run.budget} variant="inline" className="lg:hidden" />
      ) : null}

      {modificationFailed ? (
        <FailureBanner
          title="We couldn't apply that change"
          message={run.error ?? run.modification_failure?.message ?? ""}
          preserved
        />
      ) : null}

      {run.planning_failure ? (
        <FailureBanner
          title="Planning could not be completed"
          message={run.planning_failure.message}
        />
      ) : null}

      {run.operation.operation_type === "modification" ? (
        <ModificationSummary run={run} />
      ) : null}

      <div className="grid gap-3 lg:grid-cols-[240px_minmax(0,1fr)_220px] lg:items-start xl:grid-cols-[260px_minmax(0,1fr)_240px]">
        <aside className="order-2 flex flex-col gap-3 lg:order-1 lg:sticky lg:top-[3.75rem] lg:max-h-[calc(100vh-4.5rem)]">
          <ConversationPanel history={history} />
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
            {isMutating && liveExecution ? (
              <LivePlanningState execution={liveExecution} mode={planningMode} />
            ) : (
              <>
                {hasItinerary ? (
                  <p className="mb-2 text-xs text-[var(--foreground-secondary)]">
                    What would you like to change?
                  </p>
                ) : isClarifying ? (
                  <p className="mb-2 text-xs leading-relaxed text-[var(--foreground-secondary)]">
                    {clarificationPrompt(run)}
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
                  compact
                />
              </>
            )}
          </div>
        </aside>

        <main className="order-1 min-w-0 space-y-3 lg:order-2">
          {run.itinerary ? (
            <>
              <ItineraryTimeline
                key={`${run.run_id}-${run.operation.changed_item_ids.join(",")}`}
                itinerary={run.itinerary}
                affectedDays={run.operation.affected_days}
                changedItemIds={run.operation.changed_item_ids}
                selectedDay={selectedDay}
                selectedItemId={selectedItemId}
                onDayChange={setSelectedDay}
                onSelectItem={setSelectedItemId}
              />
              <ItineraryMap
                itinerary={run.itinerary}
                selectedDay={selectedDay}
                selectedItemId={selectedItemId}
                onSelectItem={setSelectedItemId}
                collapsed={mapCollapsed}
                onToggleCollapsed={() => setMapCollapsed((value) => !value)}
                className="lg:hidden"
              />
            </>
          ) : isMutating && liveExecution ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
              <LivePlanningState execution={liveExecution} mode={planningMode} />
            </div>
          ) : null}
        </main>

        <aside className="order-3 hidden flex-col gap-3 lg:sticky lg:top-[3.75rem] lg:flex">
          {run.budget ? <BudgetPanel budget={run.budget} variant="compact" /> : null}
          {run.itinerary ? (
            <ItineraryMap
              itinerary={run.itinerary}
              selectedDay={selectedDay}
              selectedItemId={selectedItemId}
              onSelectItem={setSelectedItemId}
            />
          ) : null}
        </aside>
      </div>
    </div>
  );
}
