/**
 * Shared application constants and types.
 */

export const APP_NAME = "AI Trip Planner";

export type HealthStatus = "ok" | "degraded";

export interface HealthResponse {
  status: HealthStatus;
  service: string;
}

export * from "./agent.js";
