import { test, expect } from "@playwright/test";

const DESKTOP_VIEWPORTS = [
  { width: 1440, height: 900, label: "1440x900" },
  { width: 1280, height: 800, label: "1280x800" },
  { width: 1024, height: 768, label: "1024x768" },
] as const;

test.describe("100% zoom baseline — no accidental scaling", () => {
  test.use({ deviceScaleFactor: 1 });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "__clerk_environment",
        JSON.stringify({ frontendApi: "clerk.test", publishableKey: "pk_test" }),
      );
    });
  });

  test("document has no CSS zoom or transform scaling on root elements", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/planner");

    const scaling = await page.evaluate(() => {
      const readScale = (el: Element) => {
        const style = getComputedStyle(el);
        const transform = style.transform;
        const hasScale =
          transform !== "none" && /matrix|scale/.test(transform);
        return {
          zoom: style.zoom || "1",
          transform,
          hasScale,
        };
      };

      return {
        html: readScale(document.documentElement),
        body: readScale(document.body),
        devicePixelRatio: window.devicePixelRatio,
      };
    });

    expect(scaling.html.hasScale).toBe(false);
    expect(scaling.body.hasScale).toBe(false);
    expect(["1", "normal", ""]).toContain(scaling.html.zoom);
    expect(["1", "normal", ""]).toContain(scaling.body.zoom);
    expect(scaling.devicePixelRatio).toBe(1);
  });

  for (const viewport of DESKTOP_VIEWPORTS) {
    test(`empty planner fits at authored 100% baseline ${viewport.label}`, async ({
      page,
    }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.goto("/planner");

      const metrics = await page.evaluate(() => {
        const viewportHeight = window.innerHeight;
        const scrollHeight = document.documentElement.scrollHeight;
        const isInViewport = (selector: string) => {
          const el = document.querySelector(selector);
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= viewportHeight + 1;
        };

        return {
          viewportHeight,
          scrollHeight,
          overflowPx: scrollHeight - viewportHeight,
          devicePixelRatio: window.devicePixelRatio,
          headline: isInViewport("#planner-empty-heading"),
          composer: isInViewport('[data-testid="planner-empty-composer"]'),
          cta: isInViewport('[data-testid="planner-empty-cta"]'),
          examples: isInViewport('[data-testid="planner-empty-examples"]'),
          destinations:
            isInViewport('[data-testid="planner-empty-destinations"]') ||
            isInViewport('[data-testid="planner-empty-destinations-mobile"]'),
        };
      });

      expect(metrics.devicePixelRatio).toBe(1);
      expect(metrics.overflowPx).toBeLessThanOrEqual(2);
      expect(metrics.headline).toBe(true);
      expect(metrics.composer).toBe(true);
      expect(metrics.cta).toBe(true);
      expect(metrics.examples).toBe(true);
      expect(metrics.destinations).toBe(true);
    });
  }
});
