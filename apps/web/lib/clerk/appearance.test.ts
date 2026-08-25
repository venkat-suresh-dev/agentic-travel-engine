import { describe, expect, it } from "vitest";

import { clerkAppearance } from "./appearance";

describe("clerkAppearance", () => {
  it("uses the product teal palette and light surfaces", () => {
    expect(clerkAppearance.variables?.colorPrimary).toBe("#0d5c63");
    expect(clerkAppearance.variables?.colorBackground).toBe("#fbf8f3");
    expect(clerkAppearance.variables?.colorInputBackground).toBe("#fffdf9");
    expect(clerkAppearance.variables?.colorText).toBe("#17130f");
  });

  it("keeps Clerk elements compact and product-themed", () => {
    expect(clerkAppearance.elements?.rootBox).toContain("max-w-[440px]");
    expect(clerkAppearance.elements?.formButtonPrimary).toContain(
      "bg-[var(--accent)]",
    );
    expect(clerkAppearance.elements?.card).toContain(
      "bg-[var(--surface-elevated)]",
    );
  });
});
