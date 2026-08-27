import { describe, expect, it } from "vitest";

import {
  budgetExclusionSummary,
  buildTripLogistics,
  excludedBudgetCategories,
} from "@/lib/planner/logistics";
import { completeRunFixture } from "@/test/fixtures/planner";
import type { AgentRunResponse } from "@agentic-travel-engine/shared-types";

describe("buildTripLogistics currency semantics", () => {
  it("surfaces live flight and sandbox hotel from infrastructure items", () => {
    const logistics = buildTripLogistics(completeRunFixture, 1);
    expect(logistics).not.toBeNull();
    expect(logistics?.flight.status).toBe("available");
    expect(logistics?.flight.carrier).toBe("SpiceJet");
    expect(logistics?.flight.routeLabel).toBe("Mumbai → Dubai");
    expect(logistics?.flight.priceAmount).toBe("51358");
    expect(logistics?.flight.priceCurrency).toBe("INR");
    expect(logistics?.flight.includedInBudget).toBe(true);
    expect(logistics?.flight.priceIsPartyTotal).toBe(true);
    expect(logistics?.flight.provenanceLabel).toMatch(/Live · SerpApi/i);
    expect(logistics?.stay.status).toBe("available");
    expect(logistics?.stay.name).toBe("Downtown Hotel");
    expect(logistics?.stay.nights).toBe(5);
    expect(logistics?.stay.priceAmount).toBe("18500");
    expect(logistics?.stay.priceCurrency).toBe("INR");
    expect(logistics?.stay.includedInBudget).toBe(true);
    expect(logistics?.stay.provenanceLabel).toMatch(/Sandbox · StayingAPI/i);
  });

  it("presents estimated ground travel without implying a booking", () => {
    const logistics = buildTripLogistics(completeRunFixture, 1);
    expect(logistics?.ground.status).toBe("available");
    expect(logistics?.ground.modeLabel).toBe("Driving");
    expect(logistics?.ground.provenanceLabel).toMatch(/Estimated/i);
    expect(logistics?.ground.legs[0]?.durationLabel).toBe("9 min");
    expect(logistics?.ground.legs[0]?.distanceLabel).toBe("2.8 km");
  });

  it("shows flights as unavailable when no infrastructure item exists", () => {
    const run = {
      ...completeRunFixture,
      itinerary: {
        ...completeRunFixture.itinerary!,
        infrastructure_items: completeRunFixture.itinerary!.infrastructure_items.filter(
          (item) => item.category !== "flight",
        ),
      },
    };
    const logistics = buildTripLogistics(run, 1);
    expect(logistics?.flight.status).toBe("unavailable");
  });

  it("displays converted hotel amounts in trip currency with original provenance", () => {
    const run = withConvertedHotel(completeRunFixture);
    const logistics = buildTripLogistics(run, 1);
    expect(logistics?.stay.priceAmount).toBe("190980");
    expect(logistics?.stay.priceCurrency).toBe("INR");
    expect(logistics?.stay.originalAmount).toBe("2122");
    expect(logistics?.stay.originalCurrency).toBe("EUR");
    expect(logistics?.stay.includedInBudget).toBe(true);
    expect(logistics?.stay.exclusionReason).toBeNull();
  });

  it("keeps unconverted hotel in original currency and marks exclusion", () => {
    const run = withExcludedHotel(completeRunFixture);
    const logistics = buildTripLogistics(run, 1);
    expect(logistics?.stay.priceAmount).toBe("2122");
    expect(logistics?.stay.priceCurrency).toBe("EUR");
    expect(logistics?.stay.includedInBudget).toBe(false);
    expect(logistics?.stay.exclusionReason).toMatch(/conversion is unavailable/i);
  });
});

describe("budget exclusion helpers", () => {
  it("summarizes hotel exclusion for the budget panel", () => {
    const run = withExcludedHotel(completeRunFixture);
    expect(excludedBudgetCategories(run.budget)).toHaveLength(1);
    expect(budgetExclusionSummary(run.budget)).toBe(
      "Hotel excluded — conversion unavailable",
    );
  });

  it("returns null when every category is included", () => {
    expect(budgetExclusionSummary(completeRunFixture.budget)).toBeNull();
  });
});

function withConvertedHotel(base: AgentRunResponse): AgentRunResponse {
  return {
    ...base,
    itinerary: {
      ...base.itinerary!,
      infrastructure_items: base.itinerary!.infrastructure_items.map((item) =>
        item.item_id === "hotel-checkin-1"
          ? {
              ...item,
              cost: {
                amount: "190980",
                currency: "INR",
                is_estimate: false,
                data_kind: "live",
                source_amount: "2122",
                source_currency: "EUR",
              },
            }
          : item,
      ),
    },
    budget: {
      ...base.budget!,
      categories: base.budget!.categories.map((line) =>
        line.category === "hotel"
          ? {
              ...line,
              amount: "190980",
              currency: "INR",
              included_in_total: true,
              source_amount: "2122",
              source_currency: "EUR",
            }
          : line,
      ),
    },
  };
}

function withExcludedHotel(base: AgentRunResponse): AgentRunResponse {
  return {
    ...base,
    itinerary: {
      ...base.itinerary!,
      infrastructure_items: base.itinerary!.infrastructure_items.map((item) =>
        item.item_id === "hotel-checkin-1"
          ? {
              ...item,
              cost: {
                amount: "2122",
                currency: "EUR",
                is_estimate: false,
                data_kind: "live",
              },
            }
          : item,
      ),
    },
    budget: {
      ...base.budget!,
      categories: [
        ...base.budget!.categories.filter((line) => line.category !== "hotel"),
        {
          category: "hotel",
          amount: null,
          currency: "INR",
          data_kind: "unavailable",
          included_in_total: false,
          is_estimate: false,
          source_amount: "2122",
          source_currency: "EUR",
          assumption:
            "Hotel cost not included in INR budget because currency conversion is unavailable.",
        },
      ],
    },
  };
}
