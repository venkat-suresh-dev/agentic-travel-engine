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

test.describe("Phase 7B above-the-fold QA", () => {
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
    test(`key trip state visible without scroll at ${viewport.label}`, async ({
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
        const isPartiallyInViewport = (el: Element | null) => {
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return rect.top < viewportHeight && rect.bottom > 0 && rect.top < viewportHeight * 0.92;
        };

        const destination = document.querySelector("h1");
        const budget =
          document.querySelector('[aria-label="Budget summary"]') ??
          document.querySelector("#budget-heading-compact");
        const logistics = document.querySelector('[aria-label="Trip essentials"]');
        const dayTab = document.querySelector('[role="tab"][aria-selected="true"]');
        const activity = document.querySelector('[role="tabpanel"] ol li');

        return {
          destination: isInViewport(destination),
          budget: isInViewport(budget),
          logistics: isInViewport(logistics),
          dayTab: isPartiallyInViewport(dayTab),
          activity: isPartiallyInViewport(activity),
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        };
      });

      expect(checks.scrollWidth).toBeLessThanOrEqual(checks.clientWidth + 1);
      expect(checks.destination).toBe(true);
      expect(checks.budget).toBe(true);
      expect(checks.logistics).toBe(true);
      expect(checks.dayTab).toBe(true);
      // Wide desktop: first activity should peek above the composer dock.
      if (viewport.width >= 1440 && viewport.height >= 900) {
        expect(checks.activity).toBe(true);
      }
    });
  }
});
