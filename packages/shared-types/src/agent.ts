/** Typed contracts for the agent conversation API (mirrors backend Phase 6B). */

export type ConversationOperationType =
  | "initial_plan"
  | "clarification"
  | "modification";

export type AgentRunStatus = "complete" | "needs_clarification" | "failed";

export type PriceDataKind =
  | "live"
  | "cached"
  | "estimated"
  | "free"
  | "unavailable";

export type ItineraryItemCategory =
  | "flight"
  | "hotel"
  | "attraction"
  | "restaurant"
  | "transport"
  | "free_time"
  | "other";

export type TripType = "leisure" | "business" | "family" | "adventure";

export interface ItemCost {
  amount: string | null;
  currency: string;
  is_estimate: boolean;
  data_kind: PriceDataKind;
}

export interface ItineraryItem {
  item_id: string;
  day_number: number | null;
  date: string | null;
  start_time: string;
  end_time: string;
  category: ItineraryItemCategory;
  title: string;
  description: string | null;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  cost: ItemCost;
  source: string;
  source_id: string | null;
  data_status: PriceDataKind;
}

export interface TravelLeg {
  leg_id: string;
  from_item_id: string;
  to_item_id: string;
  day_number: number;
  start_time: string;
  end_time: string;
  distance_meters: number;
  duration_seconds: number;
  travel_mode: string;
  source: string;
  data_status: PriceDataKind;
}

export interface MealSuggestion {
  day_number: number;
  item: ItineraryItem;
}

export interface ItineraryDay {
  day_number: number;
  date: string | null;
  items: ItineraryItem[];
  travel_legs: TravelLeg[];
  meal: MealSuggestion | null;
  subtotal: string;
  currency: string;
}

export interface Itinerary {
  days: ItineraryDay[];
  infrastructure_items: ItineraryItem[];
  currency: string;
  total_estimated_cost: string;
  budget_currency: string;
  budget_amount: string;
  budget_total_cost: string;
  budget_remaining: string;
}

export interface TripRequest {
  destination: string | null;
  start_date: string | null;
  end_date: string | null;
  duration_days: number | null;
  travelers: number | null;
  budget_amount: string | null;
  budget_currency: string | null;
  departure_city: string | null;
  trip_type: TripType | null;
  preferences: string[];
}

export interface Clarification {
  missing_fields: string[];
  prompts: Record<string, string>;
  message: string;
}

export interface OperationResult {
  operation_type: ConversationOperationType;
  status: AgentRunStatus;
  affected_days: number[];
  changed_item_ids: string[];
  refreshed_sources: string[];
  budget_changed: boolean;
  summary: string | null;
}

export interface BudgetSummary {
  currency: string;
  budget_amount: string;
  total_cost: string;
  remaining: string;
  budget_exceeded: boolean;
  variance: string;
}

export interface CriticSummary {
  valid: boolean;
  issue_count: number;
  warning_count: number;
  issues: string[];
  warnings: string[];
}

export interface ToolAvailability {
  aggregate_status: string | null;
  unavailable_tools: string[];
}

export interface PlanningFailure {
  message: string;
  attempts: number | null;
}

export interface ModificationFailure {
  message: string;
  issues: string[];
  preserved_itinerary: boolean;
}

export interface AgentRunResponse {
  status: AgentRunStatus;
  run_id: string;
  operation: OperationResult;
  trip_request: TripRequest | null;
  missing_fields: string[];
  clarification: Clarification | null;
  itinerary: Itinerary | null;
  budget: BudgetSummary | null;
  critic: CriticSummary | null;
  tool_availability: ToolAvailability | null;
  planning_failure: PlanningFailure | null;
  modification_failure: ModificationFailure | null;
  error: string | null;
}

export interface AgentRunCreateRequest {
  message: string;
}

export interface AgentRunMessageRequest {
  message: string;
}

export interface ApiErrorBody {
  detail?: string;
}
