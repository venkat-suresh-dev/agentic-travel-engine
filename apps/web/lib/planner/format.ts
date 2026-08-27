import type { BudgetSummary, ItineraryItem, PriceDataKind } from "@agentic-travel-engine/shared-types";

export function formatMoney(amount: string | number, currency: string): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  if (Number.isNaN(value)) {
    return `${currency} —`;
  }
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${Math.round(value).toLocaleString()}`;
  }
}

export function formatTime(time: string): string {
  const [hours, minutes] = time.split(":");
  if (hours === undefined || minutes === undefined) {
    return time;
  }
  const hour = Number(hours);
  const minute = Number(minutes);
  if (Number.isNaN(hour) || Number.isNaN(minute)) {
    return time;
  }
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}h ${remainder}m` : `${hours}h`;
}

export function formatDateRange(
  start: string | null,
  end: string | null,
  durationDays: number | null,
): string {
  if (start && end) {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const formatter = new Intl.DateTimeFormat("en", {
      month: "short",
      day: "numeric",
    });
    return `${formatter.format(startDate)} – ${formatter.format(endDate)}`;
  }
  if (durationDays) {
    return `${durationDays} days`;
  }
  return "Dates flexible";
}

export type BudgetHealth = "under" | "near" | "exact" | "over";

export function getBudgetHealth(budget: BudgetSummary): BudgetHealth {
  const remaining = Number(budget.remaining);
  const total = Number(budget.total_cost);
  const limit = Number(budget.budget_amount);
  if (budget.budget_exceeded || remaining < 0) {
    return "over";
  }
  if (Math.abs(remaining) < 1) {
    return "exact";
  }
  const ratio = total / limit;
  if (ratio >= 0.9) {
    return "near";
  }
  return "under";
}

/** Absolute amount over the requested budget (0 when within budget). */
export function budgetOverBy(budget: BudgetSummary): number {
  const remaining = Number(budget.remaining);
  if (!(budget.budget_exceeded || remaining < 0)) {
    return 0;
  }
  return Math.abs(remaining);
}

/** Human label for remaining / over-budget state — never phrases excess as “remaining”. */
export function formatBudgetBalanceLabel(budget: BudgetSummary): string {
  const health = getBudgetHealth(budget);
  if (health === "over") {
    return `${formatMoney(budgetOverBy(budget), budget.currency)} over budget`;
  }
  return `${formatMoney(budget.remaining, budget.currency)} remaining`;
}

/** Utilization percent for the progress track (capped at 100 for visual fill). */
export function budgetSpentPercent(budget: BudgetSummary): number {
  const limit = Number(budget.budget_amount);
  if (!(limit > 0)) {
    return 0;
  }
  return Math.min(100, Math.max(0, (Number(budget.total_cost) / limit) * 100));
}

/** True utilization ratio as percent (may exceed 100 when over budget). */
export function budgetUtilizationPercent(budget: BudgetSummary): number {
  const limit = Number(budget.budget_amount);
  if (!(limit > 0)) {
    return 0;
  }
  return Math.max(0, (Number(budget.total_cost) / limit) * 100);
}

export const DATA_KIND_LABELS: Record<
  PriceDataKind,
  { label: string; tone: "live" | "cached" | "estimated" | "free" | "unavailable" | "reference" }
> = {
  live: { label: "Live", tone: "live" },
  cached: { label: "Cached", tone: "cached" },
  estimated: { label: "Estimated", tone: "estimated" },
  free: { label: "Free", tone: "free" },
  reference: { label: "Reference", tone: "reference" },
  unavailable: { label: "Unavailable", tone: "unavailable" },
};

export function formatSourceLabel(item: ItineraryItem): string {
  return formatProvenanceLine(item);
}

export function formatProviderName(source: string | null | undefined): string {
  if (!source) {
    return "Provider";
  }
  const normalized = source.toLowerCase();
  if (normalized.includes("serpapi")) {
    return "SerpApi";
  }
  if (normalized.includes("stayingapi")) {
    return "StayingAPI";
  }
  if (normalized.includes("openroute")) {
    return "OpenRouteService";
  }
  if (normalized.includes("open-meteo") || normalized.includes("openmeteo")) {
    return "Open-Meteo";
  }
  if (normalized.includes("wiki")) {
    return "Wikipedia";
  }
  if (normalized.includes("geoapify")) {
    return "Geoapify";
  }
  if (normalized.includes("frankfurter")) {
    return "Frankfurter";
  }
  if (normalized.includes("google_places") || normalized.includes("google-places")) {
    return "Places";
  }
  return source
    .replace(/-google-flights$/i, "")
    .replace(/-sandbox$/i, "")
    .replaceAll("_", " ")
    .replaceAll("-", " ");
}

export function isSandboxSource(source: string | null | undefined): boolean {
  return Boolean(source && source.toLowerCase().includes("sandbox"));
}

/** Quiet provenance label for primary itinerary view — no provider names. */
export function formatShortProvenanceLabel(
  item: Pick<ItineraryItem, "category" | "data_status" | "source">,
): string {
  if (isSandboxSource(item.source)) {
    return "Sandbox";
  }
  if (item.data_status === "reference") {
    return "Reference";
  }
  if (item.data_status === "free" || item.category === "free_time") {
    return "Free";
  }
  return DATA_KIND_LABELS[item.data_status].label;
}

/** Secondary provenance detail — category or provider context for popovers. */
export function formatProvenanceDetail(
  item: Pick<ItineraryItem, "category" | "data_status" | "source">,
): string {
  if (item.data_status === "reference") {
    const type =
      item.category === "attraction" ? "Landmark" : categoryLabel(item.category);
    return type;
  }
  if (item.data_status === "estimated") {
    return categoryLabel(item.category);
  }
  return formatProviderName(item.source);
}

/** Honest short context from available fields — never invented editorial copy. */
export function formatActivityContext(
  item: Pick<
    ItineraryItem,
    "title" | "description" | "location_name" | "category"
  >,
): string | null {
  if (item.description?.trim()) {
    const text = item.description.trim();
    return text.length > 90 ? `${text.slice(0, 87)}…` : text;
  }
  if (
    item.location_name?.trim() &&
    item.location_name.trim().toLowerCase() !== item.title.trim().toLowerCase()
  ) {
    return item.location_name.trim();
  }
  if (item.category === "free_time") {
    return "Open time in your schedule";
  }
  return null;
}

export function formatProvenanceLine(
  item: Pick<ItineraryItem, "category" | "data_status" | "source">,
): string {
  if (isSandboxSource(item.source)) {
    return `Sandbox · ${formatProviderName(item.source)}`;
  }
  if (item.data_status === "reference") {
    const type = item.category === "attraction" ? "Landmark" : categoryLabel(item.category);
    return `Reference · ${type}`;
  }
  if (item.data_status === "free" || item.category === "free_time") {
    return "Free time";
  }
  const kind = DATA_KIND_LABELS[item.data_status];
  if (item.data_status === "estimated") {
    return `Estimated · ${categoryLabel(item.category)}`;
  }
  return `${kind.label} · ${formatProviderName(item.source)}`;
}

export function categoryLabel(category: ItineraryItem["category"]): string {
  const labels: Record<ItineraryItem["category"], string> = {
    flight: "Flight",
    hotel: "Hotel",
    attraction: "Activity",
    restaurant: "Meal",
    transport: "Transport",
    free_time: "Free time",
    other: "Other",
  };
  return labels[category];
}

export function nightsBetween(start: string | null, end: string | null): number | null {
  if (!start || !end) {
    return null;
  }
  const from = Date.parse(start);
  const to = Date.parse(end);
  if (Number.isNaN(from) || Number.isNaN(to) || to <= from) {
    return null;
  }
  return Math.round((to - from) / 86_400_000);
}
