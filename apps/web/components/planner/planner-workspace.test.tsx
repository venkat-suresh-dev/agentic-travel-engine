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
    expect(screen.getByText(/what would you like to change/i)).toBeInTheDocument();
    expect(screen.getAllByText("Breakfast").length).toBeGreaterThanOrEqual(1);
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
    expect(screen.getAllByText("Breakfast").length).toBeGreaterThanOrEqual(1);
  });
});
