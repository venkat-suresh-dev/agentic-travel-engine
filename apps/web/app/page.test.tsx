import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home page", () => {
  it("renders the application foundation heading", () => {
    render(<Home />);

    const plannerLinks = screen.getAllByRole("link", { name: /open planner/i });
    expect(plannerLinks.length).toBeGreaterThanOrEqual(1);
    expect(plannerLinks[0]).toHaveAttribute("href", "/planner");
    expect(screen.getByRole("heading", { name: /plan the trip/i })).toBeInTheDocument();
  });
});
