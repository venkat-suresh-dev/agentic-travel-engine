import { beforeEach, describe, expect, it, vi } from "vitest";

const authMock = vi.fn();
const headersMock = vi.fn();
const redirectMock = vi.fn((url: string) => {
  throw new Error(`REDIRECT:${url}`);
});

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => authMock(),
}));

vi.mock("next/headers", () => ({
  headers: () => headersMock(),
}));

vi.mock("next/navigation", () => ({
  redirect: (url: string) => redirectMock(url),
}));

describe("requirePlannerAuth", () => {
  beforeEach(() => {
    vi.resetModules();
    authMock.mockReset();
    headersMock.mockReset();
    redirectMock.mockClear();
    headersMock.mockResolvedValue(new Headers());
    delete process.env.PLAYWRIGHT;
    delete process.env.NEXT_PUBLIC_PLAYWRIGHT;
    delete process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  });

  it("skips auth when Playwright mode is enabled", async () => {
    process.env.PLAYWRIGHT = "1";
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test";

    const { requirePlannerAuth } = await import("./require-auth");
    await expect(requirePlannerAuth()).resolves.toBeUndefined();
    expect(authMock).not.toHaveBeenCalled();
  });

  it("skips auth when the Playwright bypass header is present", async () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test";
    headersMock.mockResolvedValue(
      new Headers({ "x-playwright-bypass-auth": "1" }),
    );

    const { requirePlannerAuth } = await import("./require-auth");
    await expect(requirePlannerAuth()).resolves.toBeUndefined();
    expect(authMock).not.toHaveBeenCalled();
  });

  it("skips auth when Clerk is not configured", async () => {
    const { requirePlannerAuth } = await import("./require-auth");
    await expect(requirePlannerAuth()).resolves.toBeUndefined();
    expect(authMock).not.toHaveBeenCalled();
  });

  it("redirects unauthenticated users to sign-in", async () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test";
    authMock.mockResolvedValue({ userId: null });

    const { requirePlannerAuth } = await import("./require-auth");
    await expect(requirePlannerAuth()).rejects.toThrow("REDIRECT:/sign-in");
  });

  it("allows authenticated users through", async () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test";
    authMock.mockResolvedValue({ userId: "user_123" });

    const { requirePlannerAuth } = await import("./require-auth");
    await expect(requirePlannerAuth()).resolves.toBeUndefined();
    expect(redirectMock).not.toHaveBeenCalled();
  });
});
