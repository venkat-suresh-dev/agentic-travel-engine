import type { PlannerSession } from "@/lib/planner/storage";

export type PlannerRunViewKind = "error" | "planning" | "unavailable" | "workspace";

export interface PlannerRunViewModel {
  kind: PlannerRunViewKind;
  showRefreshIndicator: boolean;
  showMutationError: boolean;
}

export interface PlannerRunViewInput {
  session: PlannerSession | null | undefined;
  isError: boolean;
  isLoading: boolean;
  isStarting: boolean;
  isFetching: boolean;
  isMutating: boolean;
  clientReady: boolean;
  hasPendingStart: boolean;
  hasMutationError: boolean;
}

export function resolvePlannerRunView(
  input: PlannerRunViewInput,
): PlannerRunViewModel {
  if (!input.clientReady) {
    return {
      kind: "planning",
      showRefreshIndicator: false,
      showMutationError: false,
    };
  }

  const session = input.session ?? null;
  const awaitingSession =
    !session && (input.isLoading || input.isStarting || input.hasPendingStart);

  if (input.isError && !session) {
    return {
      kind: "error",
      showRefreshIndicator: false,
      showMutationError: false,
    };
  }

  if (awaitingSession) {
    return {
      kind: "planning",
      showRefreshIndicator: false,
      showMutationError: false,
    };
  }

  if (!session) {
    return {
      kind: "unavailable",
      showRefreshIndicator: false,
      showMutationError: false,
    };
  }

  return {
    kind: "workspace",
    showRefreshIndicator:
      input.clientReady && input.isFetching && !input.isMutating,
    showMutationError: input.hasMutationError,
  };
}
