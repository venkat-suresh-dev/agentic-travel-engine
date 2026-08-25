/** SSE event contracts for live agent execution (Phase 7C). */

export type AgentRunEventType =
  | "run_started"
  | "node_started"
  | "node_completed"
  | "node_failed"
  | "tool_started"
  | "tool_completed"
  | "parallel_group_started"
  | "parallel_group_completed"
  | "run_status_changed"
  | "run_completed"
  | "run_failed"
  | "heartbeat";

export interface AgentRunEvent {
  event_id: string;
  run_id: string;
  type: AgentRunEventType;
  timestamp: string;
  node_name?: string | null;
  tool_name?: string | null;
  status?: string | null;
  duration_ms?: number | null;
  metadata?: Record<string, unknown>;
}

export const NODE_LABELS: Record<string, string> = {
  extract_requirements: "Understanding your request",
  extract_modification: "Understanding your change",
  validate_requirements: "Validating requirements",
  resolve_modification_scope: "Resolving change scope",
  retrieve_context: "Retrieving destination context",
  ask_user: "Requesting clarification",
  aggregate_independent_tools: "Aggregating sources",
  compute_budget: "Computing budget",
  build_itinerary: "Building itinerary",
  critic_validate: "Validating plan",
  apply_modification: "Applying changes",
  recompute_modification_budget: "Recomputing budget",
  convert_currency: "Converting currency",
  finalize_run: "Finalizing",
  finalize_failure: "Finalizing failure",
  finalize_modification_failure: "Finalizing modification failure",
};

export const TOOL_LABELS: Record<string, string> = {
  weather: "Weather",
  flights: "Flights",
  hotels: "Hotels",
  distance: "Distance",
  restaurants: "Restaurants",
  attractions: "Attractions",
  currency: "Currency",
};
