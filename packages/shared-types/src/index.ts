/**
 * Shared application constants and types.
 * OpenAPI-generated API contracts will be added here in a later phase.
 */

export const APP_NAME = "AI Trip Planner";

/** Placeholder for future generated API health response types. */
export type HealthStatus = "ok" | "degraded";

export interface HealthResponse {
  status: HealthStatus;
  service: string;
}
