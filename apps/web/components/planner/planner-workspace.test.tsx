import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PlannerWorkspace } from "@/components/planner/planner-workspace";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  clarificationRunFixture,
  completeRunFixture,
  failedModificationFixture,
} from "@/test/fixtures/planner";

describe("PlannerWorkspace", () => {
  it("shows clarification state before itinerary exists", () => {
    render(
      <TooltipProvider>
        <PlannerWorkspace
          session={{
            run: clarificationRunFixture,
            history: [],
          }}
          onSendMessage={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.getByText(/almost there/i)).toBeInTheDocument();
  });

  it("renders completed itinerary and modification prompt", () => {
    render(
      <TooltipProvider>
        <PlannerWorkspace
          session={{
            run: completeRunFixture,
            history: [],
          }}
          onSendMessage={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.getByText(/refine your trip/i)).toBeInTheDocument();
    expect(screen.getAllByText("Breakfast").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/trip essentials/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/flight details/i)).toBeInTheDocument();
    expect(screen.getByText("Downtown Hotel")).toBeInTheDocument();
    expect(screen.getByLabelText(/getting around details/i)).toBeInTheDocument();
  });

  it("keeps itinerary visible when modification fails", () => {
    render(
      <TooltipProvider>
        <PlannerWorkspace
          session={{
            run: failedModificationFixture,
            history: [],
          }}
          onSendMessage={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.getByText(/couldn't apply that change/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /day 02/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText("Dubai Museum")).toBeInTheDocument();
  });
});
