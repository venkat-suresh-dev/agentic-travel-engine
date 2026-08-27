import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";

import { BudgetPanel } from "@/components/planner/budget-panel";
import { FailureBanner } from "@/components/planner/failure-banner";
import { ItineraryTimeline } from "@/components/planner/itinerary-timeline";
import { ModificationSummary } from "@/components/planner/modification-summary";
import { PlannerEmptyState } from "@/components/planner/planner-empty-state";
import { ProvenanceBadge } from "@/components/planner/provenance-badge";
import { TripHeader } from "@/components/planner/trip-header";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  completeRunFixture,
  failedModificationFixture,
  modificationRunFixture,
} from "@/test/fixtures/planner";

function renderWithProviders(ui: ReactElement) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

describe("PlannerEmptyState", () => {
  it("renders premium empty state copy", () => {
    renderWithProviders(<PlannerEmptyState onSubmit={() => undefined} />);
    expect(
      screen.getByRole("heading", {
        name: /describe your trip/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("planner-empty-composer")).toBeInTheDocument();
    expect(screen.getByTestId("planner-empty-cta")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dubai · 5 days example/i })).toBeInTheDocument();
  });
});

describe("TripHeader", () => {
  it("shows destination and budget summary", () => {
    renderWithProviders(<TripHeader run={completeRunFixture} />);
    expect(screen.getByRole("heading", { name: "Dubai" })).toBeInTheDocument();
    expect(screen.getByText(/5 days · 2 travelers · Mumbai → Dubai/)).toBeInTheDocument();
    expect(screen.getByText(/₹1,44,000/i)).toBeInTheDocument();
    expect(screen.getByText(/remaining/i)).toBeInTheDocument();
  });

  it("phrases over-budget as excess, not remaining", () => {
    const overBudgetRun = {
      ...completeRunFixture,
      budget: {
        ...completeRunFixture.budget!,
        total_cost: "353113",
        remaining: "-203113",
        budget_exceeded: true,
        variance: "-203113",
      },
    };
    renderWithProviders(<TripHeader run={overBudgetRun} />);
    expect(screen.getByText(/over budget by ₹2,03,113/i)).toBeInTheDocument();
    expect(screen.queryByText(/-₹2,03,113 remaining/i)).not.toBeInTheDocument();
  });
});

describe("BudgetPanel", () => {
  it("uses authoritative backend budget values", () => {
    renderWithProviders(<BudgetPanel budget={completeRunFixture.budget!} variant="full" />);
    expect(screen.getByRole("heading", { name: /trip budget/i })).toBeInTheDocument();
  });

  it("renders compact budget snapshot", () => {
    renderWithProviders(<BudgetPanel budget={completeRunFixture.budget!} variant="compact" />);
    expect(screen.getByText(/₹1,44,000/)).toBeInTheDocument();
    expect(screen.getByText(/remaining/i)).toBeInTheDocument();
    expect(screen.getByText(/flights/i)).toBeInTheDocument();
    expect(screen.getByText(/₹51,358/)).toBeInTheDocument();
  });

  it("surfaces actionable over-budget recovery", () => {
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
    renderWithProviders(
      <BudgetPanel
        budget={budget}
        variant="compact"
        recovery={{
          primary: "Lower the trip cost",
          secondary: ["Find a cheaper hotel", "Find cheaper flights"],
          explanation:
            "Your current flight + stay combination exceeds the requested budget.",
        }}
        onApplySuggestion={() => undefined}
      />,
    );
    expect(screen.getByText(/over by ₹2,03,113/i)).toBeInTheDocument();
    expect(
      screen.getByText(/flight \+ stay combination exceeds/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /lower the trip cost/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /find a cheaper hotel/i })).toBeInTheDocument();
  });

  it("explains hotel exclusion when conversion is unavailable", () => {
    const budget = {
      ...completeRunFixture.budget!,
      categories: [
        ...completeRunFixture.budget!.categories.filter((line) => line.category !== "hotel"),
        {
          category: "hotel" as const,
          amount: null,
          currency: "INR",
          data_kind: "unavailable" as const,
          included_in_total: false,
          is_estimate: false,
          source_amount: "2122",
          source_currency: "EUR",
          assumption:
            "Hotel cost not included in INR budget because currency conversion is unavailable.",
        },
      ],
    };
    renderWithProviders(<BudgetPanel budget={budget} variant="compact" />);
    expect(screen.getByText(/hotel excluded — conversion unavailable/i)).toBeInTheDocument();
    expect(screen.getByText("Excluded")).toBeInTheDocument();
  });
});

describe("ItineraryTimeline", () => {
  it("renders day timeline with activity", () => {
    renderWithProviders(
      <ItineraryTimeline
        itinerary={completeRunFixture.itinerary!}
        affectedDays={[1]}
      />,
    );
    expect(screen.getByRole("tab", { name: /day 01/i })).toBeInTheDocument();
    expect(screen.getByText("Breakfast")).toBeInTheDocument();
    expect(screen.getAllByText(/heritage/i).length).toBeGreaterThanOrEqual(1);
  });
});

describe("ProvenanceBadge", () => {
  it("exposes provenance affordance", () => {
    renderWithProviders(
      <ProvenanceBadge
        dataKind="live"
        source="google_places"
        sourceId="places/1"
      />,
    );
    expect(
      screen.getByRole("button", {
        name: /data provenance: live/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
  });
});

describe("ModificationSummary", () => {
  it("surfaces structured operation metadata", () => {
    renderWithProviders(<ModificationSummary run={modificationRunFixture} />);
    expect(screen.getByLabelText(/modification summary/i)).toBeInTheDocument();
    expect(screen.getByText(/day 02 updated/i)).toBeInTheDocument();
    expect(screen.getByText(/2 activities → 1/i)).toBeInTheDocument();
  });
});

describe("FailureBanner", () => {
  it("preserves itinerary messaging on failed modification", () => {
    renderWithProviders(
      <FailureBanner
        title="We couldn't apply that change"
        message={failedModificationFixture.error ?? ""}
        preserved
      />,
    );
    expect(
      screen.getByText(/your previous itinerary is still intact/i),
    ).toBeInTheDocument();
  });
});
