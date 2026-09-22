import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "./AppHeader";

let pathname = "/employees/4";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

describe("AppHeader", () => {
  it("marks the current section as active", () => {
    pathname = "/employees/4";
    render(<AppHeader askAction={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Employees" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Analytics" })).not.toHaveAttribute("aria-current");
  });

  it("opens the assistant drawer from the launcher and closes it again", async () => {
    pathname = "/analytics";
    render(<AppHeader askAction={vi.fn()} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Compensation" }));
    expect(screen.getByRole("dialog", { name: "Ask Compensation" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
