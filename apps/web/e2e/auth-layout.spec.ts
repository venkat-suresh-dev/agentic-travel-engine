import { test, expect } from "@playwright/test";

test.describe.configure({ mode: "serial" });

const VIEWPORTS = [
  { width: 1440, height: 900, label: "1440x900" },
  { width: 1280, height: 800, label: "1280x800" },
  { width: 1024, height: 768, label: "1024x768" },
  { width: 768, height: 1024, label: "768x1024" },
  { width: 430, height: 932, label: "430x932" },
  { width: 390, height: 844, label: "390x844" },
  { width: 375, height: 812, label: "375x812" },
] as const;

async function measureAuthCard(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const card = document.querySelector(".cl-card");
    const slot = document.querySelector(".auth-clerk-slot");
    const cardRect = card?.getBoundingClientRect();
    const slotRect = slot?.getBoundingClientRect();
    return {
      viewportWidth: window.innerWidth,
      cardWidth: cardRect ? Math.round(cardRect.width) : 0,
      cardHeight: cardRect ? Math.round(cardRect.height) : 0,
      slotWidth: slotRect ? Math.round(slotRect.width) : 0,
      overflow:
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth + 1,
    };
  });
}

for (const route of ["/sign-in", "/sign-up"] as const) {
  test.describe(`Auth layout ${route}`, () => {
    for (const viewport of VIEWPORTS) {
      test(`compact centered card at ${viewport.label}`, async ({ page }) => {
        await page.setViewportSize({
          width: viewport.width,
          height: viewport.height,
        });
        await page.goto(route);
        await page.waitForSelector(".cl-card", { timeout: 30_000 });

        const metrics = await measureAuthCard(page);
        const isPhone = viewport.width < 640;

        expect(metrics.overflow).toBe(false);
        expect(metrics.cardWidth).toBeGreaterThan(0);
        expect(metrics.cardWidth).toBeLessThanOrEqual(460);
        expect(metrics.slotWidth).toBeLessThanOrEqual(460);

        if (isPhone) {
          expect(metrics.cardWidth).toBeLessThanOrEqual(viewport.width - 24);
          expect(metrics.cardWidth).toBeGreaterThanOrEqual(viewport.width * 0.78);
        } else {
          expect(metrics.cardWidth).toBeGreaterThanOrEqual(360);
          expect(metrics.cardWidth).toBeLessThanOrEqual(460);
        }

        expect(metrics.cardHeight).toBeLessThan(viewport.height);
      });
    }
  });
}

test("sign-in shows product branding and Clerk card", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/sign-in");
  await page.waitForSelector(".cl-card", { timeout: 30_000 });

  await expect(page.getByRole("link", { name: /AI Trip Planner/i })).toBeVisible();
  await expect(page.locator(".auth-clerk-slot .cl-card")).toBeVisible();
});

test("sign-in keeps parchment light theme and teal primary CTA", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/sign-in");
  await page.waitForSelector(".cl-formButtonPrimary", { timeout: 30_000 });

  const theme = await page.evaluate(() => {
    const bodyStyle = getComputedStyle(document.body);
    const button = document.querySelector(".cl-formButtonPrimary");
    const buttonStyle = button ? getComputedStyle(button) : null;
    const card = document.querySelector(".cl-card");
    const cardStyle = card ? getComputedStyle(card) : null;

    return {
      colorScheme: getComputedStyle(document.documentElement).colorScheme,
      bodyUsesGradient: bodyStyle.backgroundImage.includes("gradient"),
      buttonBackground: buttonStyle?.backgroundColor ?? "",
      cardBackground: cardStyle?.backgroundColor ?? "",
    };
  });

  expect(theme.colorScheme).toBe("light");
  expect(theme.bodyUsesGradient).toBe(true);
  expect(theme.buttonBackground).toMatch(/13,\s*92,\s*99/);
  expect(theme.cardBackground).not.toMatch(/rgb\((1[0-9]|2[0-4]),/);
});

test("landing open planner navigates without RSC payload error", async ({ page }) => {
  const rscErrors: string[] = [];
  page.on("console", (message) => {
    if (message.text().includes("Failed to fetch RSC payload")) {
      rscErrors.push(message.text());
    }
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByRole("link", { name: /open planner/i }).click();
  await page.waitForURL(/\/planner/);

  expect(rscErrors).toHaveLength(0);
});

test("unauthenticated landing open planner redirects to sign-in without RSC error", async ({
  browser,
}) => {
  const context = await browser.newContext({
    extraHTTPHeaders: {},
  });
  const page = await context.newPage();
  const rscErrors: string[] = [];
  page.on("console", (message) => {
    if (message.text().includes("Failed to fetch RSC payload")) {
      rscErrors.push(message.text());
    }
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByRole("link", { name: /open planner/i }).click();
  await page.waitForURL(/\/sign-in/, { timeout: 30_000 });

  expect(rscErrors).toHaveLength(0);
  await context.close();
});
