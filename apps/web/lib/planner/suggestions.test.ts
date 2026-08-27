import { describe, expect, it } from "vitest";

import { completeRunFixture } from "@/test/fixtures/planner";
import {
  buildBudgetRecoveryActions,
  buildModificationSuggestions,
} from "@/lib/planner/suggestions";

describe("buildModificationSuggestions", () => {
  it("derives suggestions from itinerary facts", () => {
    const suggestions = buildModificationSuggestions(
      completeRunFixture.itinerary,
      completeRunFixture.budget,
    );
    expect(suggestions.length).toBeGreaterThan(0);
    expect(
      suggestions.some(
        (item) => /day/i.test(item) || /hotel/i.test(item) || /cost/i.test(item),
      ),
    ).toBe(true);
    expect(suggestions.some((item) => /cheaper restaurant on Day 1/i.test(item))).toBe(
      true,
    );
  });

  it("prioritizes over-budget recovery actions", () => {
    const budget = {
      ...completeRunFixture.budget!,
      total_cost: "353113",
      remaining: "-203113",
      budget_exceeded: true,
      variance: "-203113",
      categories: [
        {
          category: "flight" as const,
          amount: "87552",
          currency: "INR",
          data_kind: "live" as const,
          included_in_total: true,
          is_estimate: false,
        },
        {
          category: "hotel" as const,
          amount: "236561",
          currency: "INR",
          data_kind: "live" as const,
          included_in_total: true,
          is_estimate: false,
        },
        {
          category: "activity" as const,
          amount: "9000",
          currency: "INR",
          data_kind: "estimated" as const,
          included_in_total: true,
          is_estimate: true,
        },
      ],
    };
    const suggestions = buildModificationSuggestions(
      completeRunFixture.itinerary,
      budget,
    );
    expect(suggestions[0]).toBe("Lower the trip cost");
    expect(suggestions).toContain("Find a cheaper hotel");
    expect(suggestions).toContain("Find cheaper flights");
  });

  it("suggests culture when shopping appears repeatedly", () => {
    const itinerary = completeRunFixture.itinerary!;
    const shoppingDay = {
      ...itinerary.days[0]!,
      items: [
        ...itinerary.days[0]!.items,
        {
          ...itinerary.days[0]!.items[0]!,
          item_id: "shop-1",
          category: "attraction" as const,
          title: "Dubai Mall",
          start_time: "14:00:00",
        },
        {
          ...itinerary.days[0]!.items[0]!,
          item_id: "shop-2",
          category: "attraction" as const,
          title: "Souk shopping",
          start_time: "16:00:00",
        },
      ],
    };
    const suggestions = buildModificationSuggestions(
      { ...itinerary, days: [shoppingDay, ...itinerary.days.slice(1)] },
      completeRunFixture.budget,
    );
    expect(suggestions).toContain("Add more culture");
  });
});

describe("buildBudgetRecoveryActions", () => {
  it("returns null when within budget", () => {
    expect(
      buildBudgetRecoveryActions(
        completeRunFixture.itinerary,
        completeRunFixture.budget,
      ),
    ).toBeNull();
  });

  it("builds feasible recovery actions when over budget", () => {
    const budget = {
      ...completeRunFixture.budget!,
      total_cost: "353113",
      remaining: "-203113",
      budget_exceeded: true,
      variance: "-203113",
      categories: [
        {
          category: "flight" as const,
          amount: "87552",
          currency: "INR",
          data_kind: "live" as const,
          included_in_total: true,
          is_estimate: false,
        },
        {
          category: "hotel" as const,
          amount: "236561",
          currency: "INR",
          data_kind: "live" as const,
          included_in_total: true,
          is_estimate: false,
        },
      ],
    };
    const recovery = buildBudgetRecoveryActions(completeRunFixture.itinerary, budget);
    expect(recovery?.primary).toBe("Lower the trip cost");
    expect(recovery?.secondary).toContain("Find a cheaper hotel");
    expect(recovery?.explanation).toMatch(/flight \+ stay/i);
  });
});
