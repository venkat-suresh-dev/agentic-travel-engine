import type { ApiErrorBody } from "@agentic-travel-engine/shared-types";

export class ApiRequestError extends Error {
  readonly status: number;
  readonly detail: string | undefined;

  constructor(status: number, detail?: string) {
    super(detail ?? `Request failed with status ${status}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

export async function parseApiError(response: Response): Promise<ApiRequestError> {
  let detail: string | undefined;
  try {
    const body = (await response.json()) as ApiErrorBody;
    detail = body.detail;
  } catch {
    detail = undefined;
  }
  return new ApiRequestError(response.status, detail);
}

export function friendlyErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) {
      return "Please sign in to continue planning.";
    }
    if (error.status === 403) {
      return "You do not have access to this trip.";
    }
    if (error.status === 404) {
      return "This planning session could not be found.";
    }
    if (error.status >= 500) {
      return "Our servers are temporarily unavailable. Please try again.";
    }
    return error.detail ?? "The planner could not complete that request. Try again.";
  }
  if (error instanceof TypeError) {
    return "Unable to reach the planner service. Check your connection.";
  }
  return "The planner could not complete that request. Try again.";
}
