import { test, expect } from "@playwright/test";

const DESKTOP_VIEWPORTS = [
  { width: 1440, height: 900, label: "1440x900" },
  { width: 1280, height: 800, label: "1280x800" },
  { width: 1024, height: 768, label: "1024x768" },
] as const;

const ALL_VIEWPORTS = [
  ...DESKTOP_VIEWPORTS,
  { width: 768, height: 1024, label: "768x1024" },
  { width: 430, height: 932, label: "430x932" },
  { width: 390, height: 844, label: "390x844" },
  { width: 375, height: 812, label: "375x812" },
] as const;

test.describe("Planner empty state viewport QA", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "__clerk_environment",
        JSON.stringify({ frontendApi: "clerk.test", publishableKey: "pk_test" }),
      );
    });
  });

  for (const viewport of DESKTOP_VIEWPORTS) {
    test(`empty planner fits above the fold at ${viewport.label}`, async ({ page }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.goto("/planner");
      await expect(
        page.getByRole("heading", { name: /plan a trip without the spreadsheet/i }),
      ).toBeVisible();

      const checks = await page.evaluate(() => {
        const viewportHeight = window.innerHeight;
        const isInViewport = (selector: string) => {
          const el = document.querySelector(selector);
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= viewportHeight + 1;
        };

        const destinations =
          document.querySelector('[data-testid="planner-empty-destinations"]') ??
          document.querySelector('[data-testid="planner-empty-destinations-mobile"]');

        return {
          headline: isInViewport("#planner-empty-heading"),
          composer: isInViewport('[data-testid="planner-empty-composer"]'),
          cta: isInViewport('[data-testid="planner-empty-cta"]'),
          examples: isInViewport('[data-testid="planner-empty-examples"]'),
          destinations: destinations
            ? (() => {
                const rect = destinations.getBoundingClientRect();
                return rect.top >= 0 && rect.bottom <= viewportHeight + 1;
              })()
            : false,
          noPageScroll: document.documentElement.scrollHeight <= viewportHeight + 2,
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        };
      });

      expect(checks.scrollWidth).toBeLessThanOrEqual(checks.clientWidth + 1);
      expect(checks.headline).toBe(true);
      expect(checks.composer).toBe(true);
      expect(checks.cta).toBe(true);
      expect(checks.examples).toBe(true);
      expect(checks.destinations).toBe(true);
      expect(checks.noPageScroll).toBe(true);
    });
  }

  for (const viewport of ALL_VIEWPORTS) {
    test(`empty planner has no horizontal overflow at ${viewport.label}`, async ({
      page,
    }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.goto("/planner");

      const overflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
      });
      expect(overflow).toBe(false);
    });
  }

  for (const viewport of [
    { width: 430, height: 932, label: "430x932" },
    { width: 390, height: 844, label: "390x844" },
    { width: 375, height: 812, label: "375x812" },
  ] as const) {
    test(`mobile primary interaction visible at ${viewport.label}`, async ({ page }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.goto("/planner");

      const checks = await page.evaluate(() => {
        const viewportHeight = window.innerHeight;
        const isInViewport = (selector: string) => {
          const el = document.querySelector(selector);
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= viewportHeight + 1;
        };

        return {
          headline: isInViewport("#planner-empty-heading"),
          composer: isInViewport('[data-testid="planner-empty-composer"]'),
          cta: isInViewport('[data-testid="planner-empty-cta"]'),
        };
      });

      expect(checks.headline).toBe(true);
      expect(checks.composer).toBe(true);
      expect(checks.cta).toBe(true);
    });
  }
});
