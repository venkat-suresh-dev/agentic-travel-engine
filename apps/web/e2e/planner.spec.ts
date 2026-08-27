import { test, expect } from "@playwright/test";

import {
  clarificationRunFixture,
  completeRunFixture,
  modificationRunFixture,
} from "../test/fixtures/planner";

const VIEWPORTS = [
  { width: 1440, height: 900, label: "1440x900" },
  { width: 1280, height: 800, label: "1280x800" },
  { width: 1024, height: 768, label: "1024x768" },
  { width: 768, height: 1024, label: "768x1024" },
  { width: 430, height: 932, label: "430x932" },
  { width: 390, height: 844, label: "390x844" },
  { width: 375, height: 812, label: "375x812" },
] as const;

test.describe("Planner core flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "__clerk_environment",
        JSON.stringify({ frontendApi: "clerk.test", publishableKey: "pk_test" }),
      );
    });

    await page.route("**/api/agent/runs", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(clarificationRunFixture),
        });
        return;
      }
      await route.continue();
    });

    await page.route("**/api/agent/runs/*", async (route) => {
      const url = route.request().url();
      if (url.includes("/messages")) {
        await route.continue();
        return;
      }
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(completeRunFixture),
        });
        return;
      }
      await route.continue();
    });

    await page.route("**/api/agent/runs/*/messages", async (route) => {
      const body = route.request().postDataJSON() as { message?: string };
      if (body.message?.toLowerCase().includes("budget")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(completeRunFixture),
        });
        return;
      }
      if (body.message?.toLowerCase().includes("relaxed")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(modificationRunFixture),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(completeRunFixture),
      });
    });
  });

  test("planner empty state and mocked planning flow", async ({ page }) => {
    await page.goto("/planner");
    await expect(
      page.getByRole("heading", {
        name: /describe your trip/i,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /dubai · 5 days example/i }),
    ).toBeVisible();
    await expect(page.getByTestId("planner-empty-cta")).toBeVisible();
  });

  test("hydrates planner workspace from GET /api/agent/runs/{run_id}", async ({
    page,
  }) => {
    const responsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" &&
        response.url().includes(`/api/agent/runs/${completeRunFixture.run_id}`),
    );
    await page.goto(`/planner/${completeRunFixture.run_id}`);
    await responsePromise;
    await expect(page.getByRole("heading", { name: "Dubai", exact: true })).toBeVisible();
    await expect(page.getByRole("tab", { name: /day 01/i })).toBeVisible();
    await expect(page.getByText(/refine your trip/i)).toBeVisible();
    await expect(page.getByText(/trip essentials/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /flight details/i })).toBeVisible();
    await expect(page.getByText("Downtown Hotel")).toBeVisible();
  });

  test("shows unavailable state when GET returns 404", async ({ page }) => {
    await page.route("**/api/agent/runs/*", async (route) => {
      const url = route.request().url();
      if (url.includes("/messages")) {
        await route.continue();
        return;
      }
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Run not found" }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto(`/planner/${completeRunFixture.run_id}`);
    await expect(page.getByText(/planning session is unavailable/i)).toBeVisible();
    await expect(page.getByText(/could not be found/i)).toBeVisible();
  });
});

test.describe("Planner responsive layout", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "__clerk_environment",
        JSON.stringify({ frontendApi: "clerk.test", publishableKey: "pk_test" }),
      );
    });

    await page.route("**/api/agent/runs/*", async (route) => {
      const url = route.request().url();
      if (url.includes("/messages")) {
        await route.continue();
        return;
      }
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(completeRunFixture),
        });
        return;
      }
      await route.continue();
    });
  });

  for (const viewport of VIEWPORTS) {
    test(`workspace renders without horizontal overflow at ${viewport.label}`, async ({
      page,
    }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      const responsePromise = page.waitForResponse(
        (response) =>
          response.request().method() === "GET" &&
          response.url().includes(`/api/agent/runs/${completeRunFixture.run_id}`),
      );
      await page.goto(`/planner/${completeRunFixture.run_id}`);
      await responsePromise;
      await expect(page.getByRole("heading", { name: "Dubai", exact: true })).toBeVisible();
      await expect(page.getByRole("tab", { name: /day 01/i })).toBeVisible();

      const overflow = await page.evaluate(() => {
        const root = document.documentElement;
        return root.scrollWidth > root.clientWidth + 1;
      });
      expect(overflow).toBe(false);
    });
  }
});
