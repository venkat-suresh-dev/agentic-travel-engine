import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { act, type ReactNode } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PlannerRunScreen } from "@/app/planner/[runId]/page";
import { TooltipProvider } from "@/components/ui/tooltip";
import { completeRunFixture } from "@/test/fixtures/planner";
import { initialLiveExecutionState } from "@/lib/planner/execution-state";
import type { PlannerSession } from "@/lib/planner/storage";

const fetchAgentRun = vi.fn();
const loadPlannerSession = vi.fn();
const loadPendingPlannerStart = vi.fn();

vi.mock("@/lib/api/agent", () => ({
  fetchAgentRun: (...args: unknown[]) => fetchAgentRun(...args),
  createAgentRun: vi.fn(),
  sendAgentRunMessage: vi.fn(),
}));

vi.mock("@/lib/planner/auth", () => ({
  usePlannerToken: () => async () => "test-token",
}));

vi.mock("@/lib/planner/storage", () => ({
  loadPlannerSession: (...args: unknown[]) => loadPlannerSession(...args),
  loadPendingPlannerStart: (...args: unknown[]) => loadPendingPlannerStart(...args),
  savePlannerSession: vi.fn(),
  savePendingPlannerStart: vi.fn(),
  clearPendingPlannerStart: vi.fn(),
}));

vi.mock("@/lib/planner/use-agent-run-stream", () => ({
  useAgentRunStream: () => ({
    execution: initialLiveExecutionState,
    error: null,
  }),
}));

const cachedSession: PlannerSession = {
  run: completeRunFixture,
  history: [],
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>{children}</TooltipProvider>
      </QueryClientProvider>
    );
  };
}

describe("PlannerRunScreen hydration", () => {
  beforeEach(() => {
    fetchAgentRun.mockReset();
    loadPlannerSession.mockReset();
    loadPendingPlannerStart.mockReset();
    fetchAgentRun.mockImplementation(() => new Promise(() => {}));
    loadPlannerSession.mockReturnValue(cachedSession);
    loadPendingPlannerStart.mockReturnValue(null);
  });

  afterEach(() => {
    document.body.replaceChildren();
  });

  it("does not use suppressHydrationWarning on the run page", () => {
    const source = readFileSync(
      path.join(process.cwd(), "app/planner/[runId]/page.tsx"),
      "utf8",
    );
    expect(source).not.toContain("suppressHydrationWarning");
  });

  it("matches server HTML on the first client render when a cached session exists", async () => {
    const Wrapper = createWrapper();
    const ui = (
      <Wrapper>
        <PlannerRunScreen runId={completeRunFixture.run_id} />
      </Wrapper>
    );

    const serverHtml = renderToString(ui);
    expect(serverHtml).toContain("Planning your trip");
    expect(serverHtml).not.toContain("Refreshing trip state");

    const container = document.createElement("div");
    document.body.appendChild(container);
    container.innerHTML = serverHtml;

    const hydrationErrors: string[] = [];
    const consoleError = vi.spyOn(console, "error").mockImplementation((...args) => {
      hydrationErrors.push(args.map(String).join(" "));
    });

    await act(async () => {
      hydrateRoot(container, ui);
    });

    expect(
      hydrationErrors.some((message) =>
        /hydration|did not match|server rendered html/i.test(message),
      ),
    ).toBe(false);

    consoleError.mockRestore();
  });

  it("can show Refreshing trip state after hydration during background refetch", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <PlannerRunScreen runId={completeRunFixture.run_id} />
      </Wrapper>,
    );

    expect(screen.getByTestId("planner-refresh-status")).toHaveTextContent(
      "Refreshing trip state…",
    );
    expect(screen.getByRole("heading", { name: "Dubai" })).toBeInTheDocument();
  });
});
