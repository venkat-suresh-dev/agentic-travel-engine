import { describe, expect, it } from "vitest";

import { ApiRequestError, friendlyErrorMessage } from "@/lib/api/errors";
import { getBudgetHealth } from "@/lib/planner/format";

describe("friendlyErrorMessage", () => {
  it("maps auth and ownership failures", () => {
    expect(friendlyErrorMessage(new ApiRequestError(401))).toMatch(/sign in/i);
    expect(friendlyErrorMessage(new ApiRequestError(403))).toMatch(/access/i);
    expect(friendlyErrorMessage(new ApiRequestError(404))).toMatch(/not be found/i);
  });
});

describe("getBudgetHealth", () => {
  it("detects over-budget state from backend summary", () => {
    expect(
      getBudgetHealth({
        currency: "INR",
        budget_amount: "100000",
        total_cost: "110000",
        remaining: "-10000",
        budget_exceeded: true,
        variance: "-10000",
      }),
    ).toBe("over");
  });
});
