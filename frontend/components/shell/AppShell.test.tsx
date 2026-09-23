import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { openAskCompensation } from "@/components/ask-compensation/launcher";
import type { AskOutcome } from "@/components/ask-compensation/types";
import { AppShell } from "./AppShell";

let pathname = "/employees/4";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

function renderShell(action = vi.fn(async (): Promise<AskOutcome> => ({ status: "unavailable", message: "Not configured." }))) {
  render(
    <AppShell askAction={action}>
      <p>Page content</p>
    </AppShell>,
  );
  return action;
}

describe("AppShell", () => {
  it("marks the current section in the navigation and renders the page", () => {
    pathname = "/employees/4";
    renderShell();

    const employees = screen.getAllByRole("link", { name: "Employees" });
    expect(employees.every((link) => link.getAttribute("aria-current") === "page")).toBe(true);
    expect(screen.getAllByRole("link", { name: "Analytics" })[0]).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("main")).toHaveTextContent("Page content");
  });

  it("opens Ask Compensation from the launcher and closes it again", async () => {
    pathname = "/analytics";
    renderShell();

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: /Ask Compensation/ })[0]);
    expect(screen.getByRole("dialog", { name: "Ask Compensation" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close Ask Compensation" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("toggles Ask Compensation with Ctrl+K", () => {
    pathname = "/";
    renderShell();

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.getByRole("dialog", { name: "Ask Compensation" })).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("asks a question handed over by a page and shows the outcome", async () => {
    pathname = "/";
    const action = renderShell();

    act(() => openAskCompensation("What is the total payroll in Germany?"));

    expect(screen.getByRole("dialog", { name: "Ask Compensation" })).toBeInTheDocument();
    await waitFor(() => expect(action).toHaveBeenCalledWith("What is the total payroll in Germany?"));
    expect(await screen.findByText("Ask Compensation is unavailable")).toBeInTheDocument();
  });
});
