import { describe, expect, it } from "vitest";

import { completeRunFixture } from "@/test/fixtures/planner";
import { resolvePlannerRunView } from "@/lib/planner/run-view";
import type { PlannerSession } from "@/lib/planner/storage";

const cachedSession: PlannerSession = {
  run: completeRunFixture,
  history: [],
};

describe("resolvePlannerRunView", () => {
  it("keeps server and first client render on planning state", () => {
    const server = resolvePlannerRunView({
      session: undefined,
      isError: false,
      isLoading: true,
      isStarting: false,
      isFetching: true,
      isMutating: false,
      clientReady: false,
      hasPendingStart: false,
      hasMutationError: false,
    });
    const firstClientWithCacheAndRefetch = resolvePlannerRunView({
      session: cachedSession,
      isError: false,
      isLoading: false,
      isStarting: false,
      isFetching: true,
      isMutating: false,
      clientReady: false,
      hasPendingStart: false,
      hasMutationError: false,
    });

    expect(server.kind).toBe("planning");
    expect(server.showRefreshIndicator).toBe(false);
    expect(firstClientWithCacheAndRefetch.kind).toBe("planning");
    expect(firstClientWithCacheAndRefetch.showRefreshIndicator).toBe(false);
  });

  it("does not show Refreshing trip state during the hydration boundary", () => {
    const firstPaint = resolvePlannerRunView({
      session: cachedSession,
      isError: false,
      isLoading: false,
      isStarting: false,
      isFetching: true,
      isMutating: false,
      clientReady: false,
      hasPendingStart: false,
      hasMutationError: false,
    });
    expect(firstPaint.showRefreshIndicator).toBe(false);
  });

  it("may show Refreshing trip state after hydration during background refetch", () => {
    const afterHydration = resolvePlannerRunView({
      session: cachedSession,
      isError: false,
      isLoading: false,
      isStarting: false,
      isFetching: true,
      isMutating: false,
      clientReady: true,
      hasPendingStart: false,
      hasMutationError: false,
    });
    expect(afterHydration.kind).toBe("workspace");
    expect(afterHydration.showRefreshIndicator).toBe(true);
  });

  it("keeps pending starts on the planning state until the mutation begins", () => {
    const view = resolvePlannerRunView({
      session: undefined,
      isError: false,
      isLoading: false,
      isStarting: false,
      isFetching: false,
      isMutating: false,
      clientReady: true,
      hasPendingStart: true,
      hasMutationError: false,
    });
    expect(view.kind).toBe("planning");
  });
});
