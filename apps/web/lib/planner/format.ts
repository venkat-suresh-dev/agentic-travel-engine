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
  const [hours, minutes] = time.split(":").map(Number);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) {
    return time;
  }
  const period = hours >= 12 ? "PM" : "AM";
  const hour12 = hours % 12 || 12;
  return `${hour12}:${minutes.toString().padStart(2, "0")} ${period}`;
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

export const DATA_KIND_LABELS: Record<
  PriceDataKind,
  { label: string; tone: "live" | "cached" | "estimated" | "free" | "unavailable" }
> = {
  live: { label: "Live", tone: "live" },
  cached: { label: "Cached", tone: "cached" },
  estimated: { label: "Estimated", tone: "estimated" },
  free: { label: "Free", tone: "free" },
  unavailable: { label: "Unavailable", tone: "unavailable" },
};

export function formatSourceLabel(item: ItineraryItem): string {
  const kind = DATA_KIND_LABELS[item.data_status];
  const provider = item.source.replace(/_/g, " ");
  return `${kind.label} · ${provider}`;
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
