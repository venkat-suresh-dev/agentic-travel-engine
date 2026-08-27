import type {
  BudgetSummary,
  Itinerary,
  ItineraryDay,
  ItineraryItem,
} from "@agentic-travel-engine/shared-types";

import { getBudgetHealth } from "@/lib/planner/format";

interface RankedSuggestion {
  text: string;
  score: number;
}

export interface BudgetRecoveryActions {
  primary: string;
  secondary: string[];
  explanation: string;
}

/** Feasible recovery actions when the trip exceeds the requested budget. */
export function buildBudgetRecoveryActions(
  itinerary: Itinerary | null | undefined,
  budget?: BudgetSummary | null,
): BudgetRecoveryActions | null {
  if (!budget || getBudgetHealth(budget) !== "over") {
    return null;
  }

  const secondary: string[] = [];
  const hotelLine = categoryAmount(budget, "hotel");
  const flightLine = categoryAmount(budget, "flight");
  const foodLine = categoryAmount(budget, "food");
  const activityLine = categoryAmount(budget, "activity");
  const limit = Number(budget.budget_amount);
  const total = Number(budget.total_cost);

  if (hotelLine > 0 && hotelLine / Math.max(total, 1) >= 0.25) {
    secondary.push("Find a cheaper hotel");
  } else if (hotelItem(itinerary) && hotelLine > 0) {
    secondary.push("Find a cheaper hotel");
  }

  if (flightLine > 0 && flightLine / Math.max(total, 1) >= 0.12) {
    secondary.push("Find cheaper flights");
  } else if (flightItem(itinerary) && flightLine > 0) {
    secondary.push("Find cheaper flights");
  }

  if (activityLine > 0 && activityLine / Math.max(limit, 1) >= 0.05) {
    secondary.push("Reduce activity spend");
  } else if (foodLine > 0 && foodLine / Math.max(limit, 1) >= 0.05) {
    secondary.push("Find a cheaper restaurant");
  }

  const explanation =
    flightLine > 0 && hotelLine > 0
      ? "Your current flight + stay combination exceeds the requested budget."
      : hotelLine > flightLine && hotelLine > 0
        ? "Your current stay exceeds the requested budget."
        : flightLine > 0
          ? "Your current flight exceeds the requested budget."
          : "This plan exceeds the requested budget.";

  return {
    primary: "Lower the trip cost",
    secondary: secondary.slice(0, 3),
    explanation,
  };
}

export function buildModificationSuggestions(
  itinerary: Itinerary | null | undefined,
  budget?: BudgetSummary | null,
): string[] {
  if (!itinerary || itinerary.days.length === 0) {
    return [];
  }

  const ranked: RankedSuggestion[] = [];
  const recovery = buildBudgetRecoveryActions(itinerary, budget);
  if (recovery) {
    ranked.push({ text: recovery.primary, score: 110 });
    for (const [index, action] of recovery.secondary.entries()) {
      ranked.push({ text: action, score: 105 - index });
    }
  } else if (budget && Number(budget.budget_amount) > 0) {
    const used = Number(budget.total_cost) / Number(budget.budget_amount);
    if (used >= 0.85) {
      ranked.push({ text: "Lower the trip cost", score: 100 });
    }
  }

  const busiest = busiestDay(itinerary.days);
  if (busiest && attractionCount(busiest) >= 2) {
    ranked.push({
      text: `Make Day ${busiest.day_number} slower`,
      score: recovery ? 72 : 90,
    });
  }

  const expensiveMeal = mostExpensiveRestaurant(itinerary.days);
  if (expensiveMeal) {
    const mealLabel = expensiveMeal.isDinner ? "dinner" : "restaurant";
    ranked.push({
      text: `Find a cheaper ${mealLabel} on Day ${expensiveMeal.day_number}`,
      score: recovery ? 68 : 80,
    });
  }

  const travelHeavy = mostTravelDay(itinerary.days);
  if (travelHeavy && travelMinutes(travelHeavy) >= 25) {
    ranked.push({
      text: `Reduce travel on Day ${travelHeavy.day_number}`,
      score: recovery ? 60 : 70,
    });
  }

  if (shoppingCount(itinerary) >= 2) {
    ranked.push({ text: "Add more culture", score: 65 });
  }

  const repeated = repeatedCategoryLabel(itinerary);
  if (repeated) {
    ranked.push({ text: `Add more variety to ${repeated}`, score: 58 });
  }

  if (hasLowVariety(itinerary)) {
    ranked.push({ text: "Add more variety", score: 62 });
  }

  const outdoorDay = itinerary.days.find((day) => outdoorCount(day) >= 2);
  if (outdoorDay) {
    ranked.push({
      text: `Move outdoor plans off Day ${outdoorDay.day_number}`,
      score: 55,
    });
  }

  const hotel = hotelItem(itinerary);
  if (!recovery && hotel && budget && Number(budget.budget_amount) > 0) {
    const hotelShare =
      Number(hotel.cost.amount ?? 0) / Number(budget.budget_amount);
    if (hotelShare >= 0.35) {
      ranked.push({ text: "Change the hotel", score: 50 });
    }
  } else if (!recovery && hotel && ranked.length < 2) {
    ranked.push({ text: "Change the hotel", score: 40 });
  }

  const unique = new Map<string, RankedSuggestion>();
  for (const item of ranked.sort((left, right) => right.score - left.score)) {
    if (!unique.has(item.text)) {
      unique.set(item.text, item);
    }
  }
  return [...unique.values()].slice(0, 4).map((item) => item.text);
}

function categoryAmount(budget: BudgetSummary, category: string): number {
  const line = budget.categories?.find(
    (entry) =>
      entry.category === category &&
      entry.included_in_total &&
      entry.amount !== null,
  );
  return line?.amount != null ? Number(line.amount) : 0;
}

function attractionCount(day: ItineraryDay): number {
  return day.items.filter((item) => item.category === "attraction").length;
}

function outdoorCount(day: ItineraryDay): number {
  return day.items.filter((item) => {
    if (item.category !== "attraction") {
      return false;
    }
    const haystack = `${item.title} ${item.description ?? ""}`.toLowerCase();
    return /park|beach|outdoor|garden|marina/.test(haystack);
  }).length;
}

function travelMinutes(day: ItineraryDay): number {
  return Math.round(
    day.travel_legs.reduce((sum, leg) => sum + leg.duration_seconds, 0) / 60,
  );
}

function busiestDay(days: ItineraryDay[]): ItineraryDay | undefined {
  return [...days].sort(
    (left, right) =>
      attractionCount(right) - attractionCount(left) ||
      travelMinutes(right) - travelMinutes(left),
  )[0];
}

function mostTravelDay(days: ItineraryDay[]): ItineraryDay | undefined {
  return [...days].sort(
    (left, right) => travelMinutes(right) - travelMinutes(left),
  )[0];
}

function mostExpensiveRestaurant(
  days: ItineraryDay[],
): { day_number: number; isDinner: boolean } | undefined {
  let best: { day_number: number; amount: number; isDinner: boolean } | undefined;
  for (const day of days) {
    for (const item of day.items) {
      if (item.category !== "restaurant" || item.cost.amount === null) {
        continue;
      }
      const amount = Number(item.cost.amount);
      if (!best || amount > best.amount) {
        best = {
          day_number: day.day_number,
          amount,
          isDinner: isDinnerItem(item.title, item.start_time),
        };
      }
    }
  }
  return best;
}

function isDinnerItem(title: string, startTime: string): boolean {
  if (/dinner|supper|evening/i.test(title)) {
    return true;
  }
  return startTime >= "17:00:00";
}

function hotelItem(itinerary: Itinerary | null | undefined): ItineraryItem | undefined {
  return itinerary?.infrastructure_items.find((item) => item.category === "hotel");
}

function flightItem(itinerary: Itinerary | null | undefined): ItineraryItem | undefined {
  return itinerary?.infrastructure_items.find((item) => item.category === "flight");
}

function shoppingCount(itinerary: Itinerary): number {
  return itinerary.days.reduce((total, day) => {
    return (
      total +
      day.items.filter((item) => {
        const haystack =
          `${item.title} ${item.description ?? ""} ${item.location_name ?? ""}`.toLowerCase();
        return /shop|mall|souk|bazaar|market|outlet/.test(haystack);
      }).length
    );
  }, 0);
}

function repeatedCategoryLabel(itinerary: Itinerary): string | null {
  const counts = new Map<string, number>();
  for (const day of itinerary.days) {
    for (const item of day.items) {
      if (item.category === "restaurant" || item.category === "free_time") {
        continue;
      }
      counts.set(item.category, (counts.get(item.category) ?? 0) + 1);
    }
  }
  const repeated = [...counts.entries()].find(([, count]) => count >= 3);
  if (!repeated) {
    return null;
  }
  return repeated[0] === "attraction"
    ? "the activities"
    : repeated[0].replaceAll("_", " ");
}

function hasLowVariety(itinerary: Itinerary): boolean {
  const attractions = itinerary.days.flatMap((day) =>
    day.items.filter((item) => item.category === "attraction"),
  );
  const uniqueTitles = new Set(attractions.map((item) => item.title.toLowerCase()));
  if (attractions.length >= 4 && uniqueTitles.size < attractions.length * 0.7) {
    return true;
  }
  const sourceIds = attractions
    .map((item) => item.source_id)
    .filter((id): id is string => Boolean(id));
  return new Set(sourceIds).size < sourceIds.length;
}
