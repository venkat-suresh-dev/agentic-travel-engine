import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuthShell } from "./auth-shell";

describe("AuthShell", () => {
  it("renders product identity and a bounded Clerk slot", () => {
    render(
      <AuthShell>
        <div data-testid="clerk-form">Clerk form</div>
      </AuthShell>,
    );

    expect(
      screen.getByText(/grounded travel intelligence/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /AI Trip Planner/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("clerk-form")).toBeInTheDocument();

    const slot = document.querySelector(".auth-clerk-slot");
    expect(slot).not.toBeNull();
    expect(slot?.className).toContain("max-w-[440px]");
  });
});
