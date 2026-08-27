import { expect, test } from "@playwright/test";

import { completeRunFixture } from "../test/fixtures/planner";

const SSE_EVENTS = [
  {
    event_id: "1",
    run_id: "run-complete-1",
    type: "run_started",
    timestamp: new Date().toISOString(),
  },
  {
    event_id: "2",
    run_id: "run-complete-1",
    type: "node_started",
    timestamp: new Date().toISOString(),
    node_name: "extract_requirements",
    status: "running",
  },
  {
    event_id: "3",
    run_id: "run-complete-1",
    type: "node_completed",
    timestamp: new Date().toISOString(),
    node_name: "extract_requirements",
    status: "success",
    duration_ms: 120,
  },
  {
    event_id: "4",
    run_id: "run-complete-1",
    type: "tool_started",
    timestamp: new Date().toISOString(),
    tool_name: "flights",
    status: "running",
  },
  {
    event_id: "5",
    run_id: "run-complete-1",
    type: "tool_completed",
    timestamp: new Date().toISOString(),
    tool_name: "flights",
    status: "success",
    duration_ms: 900,
  },
  {
    event_id: "6",
    run_id: "run-complete-1",
    type: "run_completed",
    timestamp: new Date().toISOString(),
    status: "complete",
    duration_ms: 1800,
  },
];

function sseBody(events: typeof SSE_EVENTS): string {
  return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("");
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "__clerk_environment",
      JSON.stringify({ frontendApi: "clerk.test", publishableKey: "pk_test" }),
    );
  });
});

test("shows trace drawer and map on completed run", async ({ page }) => {
  await page.route("**/api/agent/runs/run-complete-1", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: completeRunFixture });
      return;
    }
    await route.continue();
  });

  await page.route("**/api/agent/runs/run-complete-1/stream", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sseBody(SSE_EVENTS),
    });
  });

  await page.goto("/planner/run-complete-1");
  await expect(page.getByRole("heading", { level: 1, name: "Dubai" })).toBeVisible();
  await expect(page.getByRole("button", { name: /View execution|Agent run/i })).toBeVisible();
  await page.getByRole("button", { name: /View execution|Agent run/i }).click();
  const trace = page.getByRole("dialog");
  await expect(trace.getByText("Live · serpapi")).toBeVisible();
  await expect(trace.getByText("Sandbox · stayingapi")).toBeVisible();
  await expect(trace.getByText("Unavailable")).toHaveCount(0);
  await expect(page.getByLabel("Itinerary map")).toBeVisible();
});
