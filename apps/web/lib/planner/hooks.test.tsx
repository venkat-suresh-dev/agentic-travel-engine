import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { ApiRequestError } from "@/lib/api/errors";
import { plannerRunKey, usePlannerSession } from "@/lib/planner/hooks";
import { completeRunFixture } from "@/test/fixtures/planner";

const fetchAgentRun = vi.fn();

vi.mock("@/lib/api/agent", () => ({
  fetchAgentRun: (...args: unknown[]) => fetchAgentRun(...args),
  createAgentRun: vi.fn(),
  sendAgentRunMessage: vi.fn(),
}));

vi.mock("@/lib/planner/auth", () => ({
  usePlannerToken: () => async () => "test-token",
}));

vi.mock("@/lib/planner/storage", () => ({
  loadPlannerSession: vi.fn(() => null),
  savePlannerSession: vi.fn(),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("usePlannerSession", () => {
  it("hydrates run state from GET /api/agent/runs/{run_id}", async () => {
    fetchAgentRun.mockResolvedValueOnce(completeRunFixture);

    const { result } = renderHook(() => usePlannerSession("run-complete-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchAgentRun).toHaveBeenCalledWith("run-complete-1", "test-token");
    expect(result.current.data?.run.run_id).toBe("run-complete-1");
  });

  it("surfaces hydration errors from the API", async () => {
    fetchAgentRun.mockRejectedValueOnce(new ApiRequestError(404, "Run not found"));

    const { result } = renderHook(() => usePlannerSession("missing-run"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiRequestError);
    expect((result.current.error as ApiRequestError).status).toBe(404);
  });
});

describe("plannerRunKey", () => {
  it("creates a stable query key", () => {
    expect(plannerRunKey("abc")).toEqual(["planner-run", "abc"]);
  });
});
