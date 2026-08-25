import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home page", () => {
  it("renders the application foundation heading", () => {
    render(<Home />);

    expect(
      screen.getByRole("link", { name: /open planner/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open planner/i })).toHaveAttribute(
      "href",
      "/planner",
    );
  });
});
