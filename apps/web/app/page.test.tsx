import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home page", () => {
  it("renders the application foundation heading", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: /ai trip planner/i }),
    ).toBeInTheDocument();
  });
});
