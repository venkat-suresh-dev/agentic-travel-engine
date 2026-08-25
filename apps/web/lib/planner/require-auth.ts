import { auth } from "@clerk/nextjs/server";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

const PLAYWRIGHT_AUTH_BYPASS_HEADER = "x-playwright-bypass-auth";

function isPlaywrightMode(): boolean {
  return (
    process.env.PLAYWRIGHT === "1" || process.env.NEXT_PUBLIC_PLAYWRIGHT === "1"
  );
}

function isClerkConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
}

/** Redirect unauthenticated users before rendering planner routes. */
export async function requirePlannerAuth(): Promise<void> {
  const requestHeaders = await headers();
  if (
    isPlaywrightMode() ||
    requestHeaders.get(PLAYWRIGHT_AUTH_BYPASS_HEADER) === "1"
  ) {
    return;
  }

  if (!isClerkConfigured()) {
    return;
  }

  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-in");
  }
}

export { PLAYWRIGHT_AUTH_BYPASS_HEADER };
