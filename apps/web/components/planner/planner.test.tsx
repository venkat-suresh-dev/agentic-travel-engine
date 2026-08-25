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
        name: /plan a trip without the spreadsheet/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("planner-empty-composer")).toBeInTheDocument();
    expect(screen.getByTestId("planner-empty-cta")).toBeInTheDocument();
    expect(screen.getByTestId("planner-empty-destinations")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dubai · 5 days example/i })).toBeInTheDocument();
  });
});

describe("TripHeader", () => {
  it("shows destination and budget summary", () => {
    renderWithProviders(<TripHeader run={completeRunFixture} />);
    expect(screen.getByRole("heading", { name: "Dubai" })).toBeInTheDocument();
    expect(screen.getByText(/₹1,44,000/i)).toBeInTheDocument();
  });
});

describe("BudgetPanel", () => {
  it("uses authoritative backend budget values", () => {
    renderWithProviders(<BudgetPanel budget={completeRunFixture.budget!} variant="full" />);
    expect(
      screen.getByRole("heading", { name: /how your budget is tracking/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/₹1,50,000/).length).toBeGreaterThanOrEqual(1);
  });

  it("renders compact budget snapshot", () => {
    renderWithProviders(<BudgetPanel budget={completeRunFixture.budget!} variant="compact" />);
    expect(screen.getByText(/₹1,44,000/)).toBeInTheDocument();
    expect(screen.getByText(/remaining/i)).toBeInTheDocument();
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
    expect(screen.getByText(/your day-by-day plan/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /day 01/i })).toBeInTheDocument();
    expect(screen.getByText("Breakfast")).toBeInTheDocument();
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
        name: /data provenance: live from google places/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
  });
});

describe("ModificationSummary", () => {
  it("surfaces structured operation metadata", () => {
    renderWithProviders(<ModificationSummary run={modificationRunFixture} />);
    expect(screen.getByLabelText(/modification summary/i)).toBeInTheDocument();
    expect(screen.getByText(/^Day 2$/)).toBeInTheDocument();
    expect(screen.getByText(/budget recalculated/i)).toBeInTheDocument();
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
