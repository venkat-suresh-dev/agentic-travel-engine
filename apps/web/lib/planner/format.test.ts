import { describe, expect, it } from "vitest";

import { ApiRequestError, friendlyErrorMessage } from "@/lib/api/errors";
import {
  budgetOverBy,
  formatBudgetBalanceLabel,
  getBudgetHealth,
  formatTime,
} from "@/lib/planner/format";

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
        categories: [],
      }),
    ).toBe("over");
  });
});

describe("formatBudgetBalanceLabel", () => {
  it("labels excess as over budget", () => {
    expect(
      formatBudgetBalanceLabel({
        currency: "INR",
        budget_amount: "150000",
        total_cost: "353113",
        remaining: "-203113",
        budget_exceeded: true,
        variance: "-203113",
        categories: [],
      }),
    ).toMatch(/over budget/i);
    expect(
      budgetOverBy({
        currency: "INR",
        budget_amount: "150000",
        total_cost: "353113",
        remaining: "-203113",
        budget_exceeded: true,
        variance: "-203113",
        categories: [],
      }),
    ).toBe(203113);
  });
});

describe("formatTime", () => {
  it("formats itinerary times as 24-hour clock", () => {
    expect(formatTime("09:00:00")).toBe("09:00");
    expect(formatTime("17:05:00")).toBe("17:05");
  });
});
