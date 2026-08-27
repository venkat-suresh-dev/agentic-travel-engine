"use client";

import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";
import { useCallback, useMemo, useState } from "react";

import { BudgetPanel } from "@/components/planner/budget-panel";
import { ConversationPanel } from "@/components/planner/conversation-panel";
import { FailureBanner } from "@/components/planner/failure-banner";
import { ItineraryMap } from "@/components/planner/itinerary-map";
import { ItineraryTimeline } from "@/components/planner/itinerary-timeline";
import { LivePlanningState } from "@/components/planner/live-planning-state";
import { ModificationSummary } from "@/components/planner/modification-summary";
import { PlannerComposer, type ComposerDraft } from "@/components/planner/planner-composer";
import { TraceDrawer } from "@/components/planner/trace-drawer";
import { TripHeader } from "@/components/planner/trip-header";
import { TripLogistics } from "@/components/planner/trip-logistics";
import type { LiveExecutionState } from "@/lib/planner/execution-state";
import { buildTripLogistics } from "@/lib/planner/logistics";
import {
  buildBudgetRecoveryActions,
  buildModificationSuggestions,
} from "@/lib/planner/suggestions";
import type { PlannerSession } from "@/lib/planner/storage";
import { cn } from "@/lib/utils";

interface PlannerWorkspaceProps {
  session: PlannerSession | null;
  isMutating?: boolean;
  planningMode?: "initial" | "clarification" | "modification";
  execution?: LiveExecutionState;
  onSendMessage: (message: string) => Promise<void>;
  className?: string;
}

function clarificationPrompt(run: AgentRunResponse): string {
  if (run.clarification?.message) {
    return run.clarification.message;
  }
  if (run.missing_fields.length > 0) {
    return `Still needed: ${run.missing_fields.join(", ")}`;
  }
  return "Add the missing trip details to continue.";
}

function planningFailureCopy(run: AgentRunResponse): {
  title: string;
  message: string;
  detail?: string;
} {
  const failure = run.planning_failure?.message ?? "Planning could not be completed.";
  const tools = run.tool_availability?.tools ?? [];
  const succeeded = tools.filter((tool) => tool.status === "success");
  const failed = tools.filter(
    (tool) => tool.status === "unavailable" || tool.status === "error",
  );
  if (failed.length === 0) {
    return { title: "Planning could not be completed", message: failure };
  }
  const failedLabel = failed
    .map((tool) => tool.provider ?? tool.tool_name.replaceAll("_", " "))
    .join(", ");
  const succeededNames = succeeded
    .map((tool) =>
      tool.tool_name
        .replace("search_", "")
        .replace("fetch_", "")
        .replace("get_", "")
        .replaceAll("_", " "),
    )
    .slice(0, 4);
  const stillWorked =
    succeededNames.length > 0
      ? `Your itinerary still uses verified ${succeededNames.join(", ")} data.`
      : undefined;
  const nextStep = `Try again when ${failedLabel} is available.`;
  return {
    title: `${failedLabel} is temporarily unavailable.`,
    message: failure,
    detail: stillWorked ? `${stillWorked} ${nextStep}` : nextStep,
  };
}

function TraceControl({
  run,
  liveExecution,
  isMutating,
}: {
  run: AgentRunResponse;
  liveExecution?: LiveExecutionState;
  isMutating: boolean;
}) {
  if (liveExecution) {
    return (
      <TraceDrawer
        run={run}
        execution={liveExecution}
        isLive={isMutating || liveExecution.isActive}
      />
    );
  }
  if (run.tool_availability || run.critic) {
    return (
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
    );
  }
  return null;
}

export function PlannerWorkspace({
  session,
  isMutating = false,
  planningMode = "initial",
  execution,
  onSendMessage,
  className,
}: PlannerWorkspaceProps) {
  const run = session?.run;
  const history = session?.history ?? [];
  const hasItinerary = Boolean(run?.itinerary);
  const isClarifying = run?.status === "needs_clarification";
  const modificationFailed =
    run?.status === "failed" && run.modification_failure?.preserved_itinerary;
  const liveExecution = execution;
  const affectedDays = run?.operation.affected_days ?? [];
  const affectedKey = affectedDays.join(",");
  const fallbackDay =
    affectedDays.length > 0
      ? Math.min(...affectedDays)
      : (run?.itinerary?.days[0]?.day_number ?? 1);
  const selectionContext = `${run?.run_id ?? ""}:${affectedKey}`;
  const [daySelection, setDaySelection] = useState<{
    context: string;
    day: number;
  }>({ context: selectionContext, day: fallbackDay });
  const selectedDay =
    daySelection.context === selectionContext ? daySelection.day : fallbackDay;
  const setSelectedDay = (day: number) => {
    setDaySelection({ context: selectionContext, day });
  };
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [mapCollapsed, setMapCollapsed] = useState(true);
  const [composerDraft, setComposerDraft] = useState<ComposerDraft | null>(null);
  const applySuggestion = useCallback((text: string) => {
    setComposerDraft({ text, key: Date.now() });
  }, []);
  const suggestions = useMemo(
    () => buildModificationSuggestions(run?.itinerary, run?.budget),
    [run?.itinerary, run?.budget],
  );
  const recovery = useMemo(
    () => buildBudgetRecoveryActions(run?.itinerary, run?.budget),
    [run?.itinerary, run?.budget],
  );
  const logistics = useMemo(
    () => (run ? buildTripLogistics(run, selectedDay) : null),
    [run, selectedDay],
  );

  if (!run) {
    return null;
  }

  const planningFailure = run.planning_failure ? planningFailureCopy(run) : null;
  const trace = (
    <TraceControl run={run} liveExecution={liveExecution} isMutating={isMutating} />
  );

  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      <div className="min-h-0 flex-1 overflow-y-auto scrollbar-subtle">
        <div className="flex flex-col gap-5 pb-4">
          {/* Trip hero — destination, budget, essentials */}
          <div className="space-y-3">
            <TripHeader run={run} trace={trace} />

            {modificationFailed ? (
              <FailureBanner
                title="We couldn't apply that change"
                message={run.error ?? run.modification_failure?.message ?? ""}
                preserved
              />
            ) : null}

            {planningFailure ? (
              <FailureBanner
                title={planningFailure.title}
                message={planningFailure.message}
                detail={planningFailure.detail}
              />
            ) : null}

            {run.operation.operation_type === "modification" ? (
              <ModificationSummary run={run} />
            ) : null}

            {logistics ? <TripLogistics logistics={logistics} /> : null}

            {run.budget ? (
              <BudgetPanel
                budget={run.budget}
                variant="compact"
                hideSummary
                recovery={recovery}
                onApplySuggestion={applySuggestion}
              />
            ) : null}
          </div>

          {!hasItinerary && !isMutating ? (
            <div className="py-8">
              <p className="font-display text-xl text-[var(--foreground)]">Almost there</p>
              <p className="mt-2 max-w-md text-sm leading-relaxed text-[var(--foreground-secondary)]">
                Once the missing details are provided, we will search live travel data
                and compose your itinerary here.
              </p>
            </div>
          ) : null}

          {/* Itinerary hero */}
          {hasItinerary && run.itinerary ? (
            <div className="space-y-4">
              {recovery && run.budget ? (
                <BudgetPanel
                  budget={run.budget}
                  recovery={recovery}
                  onApplySuggestion={applySuggestion}
                  mobileRecoveryOnly
                  className="lg:hidden"
                />
              ) : null}

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

              <ItineraryMap
                itinerary={run.itinerary}
                selectedDay={selectedDay}
                selectedItemId={selectedItemId}
                onSelectItem={setSelectedItemId}
                className="hidden lg:block"
              />
            </div>
          ) : null}
        </div>
      </div>

      <div className="shrink-0 border-t border-[var(--border)]/60 bg-[var(--background)]/94 pt-4 backdrop-blur-md">
        {isMutating && liveExecution ? (
          <LivePlanningState execution={liveExecution} mode={planningMode} />
        ) : (
          <>
            {isClarifying && !hasItinerary ? (
              <p className="mb-3 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                {clarificationPrompt(run)}
              </p>
            ) : null}
            <PlannerComposer
              key={composerDraft?.key ?? "composer"}
              loading={isMutating}
              disabled={!run}
              title={hasItinerary ? "Refine your trip" : undefined}
              description={
                hasItinerary ? "What would you like to change?" : undefined
              }
              placeholder={
                hasItinerary
                  ? "Make day 2 more relaxed."
                  : "Add the missing details or refine your request…"
              }
              submitLabel={hasItinerary ? "Apply change" : "Continue planning"}
              suggestions={hasItinerary ? suggestions : []}
              initialMessage={composerDraft?.text ?? ""}
              onSubmit={onSendMessage}
              compact
            />
            <ConversationPanel history={history} />
          </>
        )}
      </div>
    </div>
  );
}
