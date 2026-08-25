import { test, expect } from "@playwright/test";

import { completeRunFixture } from "../test/fixtures/planner";

const VIEWPORTS = [
  { width: 1440, height: 900, label: "1440x900" },
  { width: 1280, height: 800, label: "1280x800" },
  { width: 1024, height: 768, label: "1024x768" },
  { width: 768, height: 1024, label: "768x1024" },
  { width: 430, height: 932, label: "430x932" },
  { width: 390, height: 844, label: "390x844" },
  { width: 375, height: 812, label: "375x812" },
] as const;

test.describe("Live local stack", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "__clerk_environment",
        JSON.stringify({ frontendApi: "clerk.test", publishableKey: "pk_test" }),
      );
    });
  });

  test("frontend proxy reaches FastAPI for agent routes", async ({ request }) => {
    const response = await request.post("http://localhost:3002/api/agent/runs", {
      data: { message: "Plan a 5-day trip to Dubai for 2 people." },
    });
    expect(response.status()).toBe(401);
  });

  test("planner empty state renders against live Next.js", async ({ page }) => {
    await page.goto("/planner");
    await expect(
      page.getByRole("heading", {
        name: /plan a trip without the spreadsheet/i,
      }),
    ).toBeVisible();
  });

  test("unknown run hydrates through live proxy and shows auth guidance", async ({
    page,
  }) => {
    await page.goto("/planner/unknown-live-run");
    await expect(page.getByText(/planning session is unavailable/i)).toBeVisible();
    await expect(page.getByText(/sign in to continue planning/i)).toBeVisible();
  });

  test("sign-in route is reachable when Clerk is configured", async ({ page }) => {
    const response = await page.goto("/sign-in");
    if (!response || response.status() >= 500) {
      test.skip(true, "Clerk keys are not configured in this environment");
    }
    await expect(
      page.getByRole("heading", { name: /sign in to your planner/i }),
    ).toBeVisible();
  });
});

test.describe("Live stack Phase 7B layout", () => {
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
    test(`above-the-fold layout at ${viewport.label} on live Next.js`, async ({
      page,
    }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.goto(`/planner/${completeRunFixture.run_id}`);
      await expect(page.getByRole("heading", { name: "Dubai", exact: true })).toBeVisible();

      const checks = await page.evaluate(() => {
        const viewportHeight = window.innerHeight;
        const isInViewport = (el: Element | null) => {
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= viewportHeight + 1;
        };

        return {
          destination: isInViewport(document.querySelector("h1")),
          budget:
            isInViewport(document.querySelector('[aria-label="Budget summary"]')) ||
            isInViewport(document.querySelector("#budget-heading-compact")),
          dayTab: isInViewport(
            document.querySelector('[role="tab"][aria-selected="true"]'),
          ),
          activity: isInViewport(document.querySelector("ol li")),
          overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        };
      });

      expect(checks.overflow).toBe(false);
      expect(checks.destination).toBe(true);
      expect(checks.budget).toBe(true);
      expect(checks.dayTab).toBe(true);
      expect(checks.activity).toBe(true);
    });
  }
});
