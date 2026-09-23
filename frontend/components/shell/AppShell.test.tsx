import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { openAskCompensation } from "@/components/ask-compensation/launcher";
import type { AskOutcome } from "@/components/ask-compensation/types";
import type { QueryPlan } from "@/types/ask";
import { AppShell } from "./AppShell";

let pathname = "/employees/4";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

function renderShell(
  action = vi.fn(async (): Promise<AskOutcome> => ({
    status: "unavailable",
    message: "Not configured.",
  })),
) {
  render(
    <AppShell askAction={action}>
      <p>Page content</p>
    </AppShell>,
  );
  return action;
}

describe("AppShell", () => {
  it("marks the current section in navigation", () => {
    pathname = "/employees/4";
    renderShell();

    const employees = screen.getAllByRole("link", { name: "Employees" });
    expect(employees.every((link) => link.getAttribute("aria-current") === "page")).toBe(true);
    expect(screen.getByRole("main")).toHaveTextContent("Page content");
  });

  it("opens and closes Ask Compensation", async () => {
    pathname = "/analytics";
    renderShell();

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

  it("passes prior validated query intent to follow-up questions", async () => {
    pathname = "/";
    const plan: QueryPlan = {
      select: [
        {
          alias: "payroll",
          label: "Total payroll",
          format: "currency",
          expression: {
            kind: "aggregate",
            function: "sum",
            field: "salary_usd",
            where: [{ field: "country", operator: "equals", value: "Germany" }],
          },
        },
      ],
      where: [],
      group_by: [],
      distinct: false,
      order_by: [],
      limit: 50,
    };
    const firstOutcome: AskOutcome = {
      status: "answered",
      response: {
        status: "answered",
        question: "What is the total payroll in Germany?",
        answer: "Total payroll: USD 1000.00.",
        interpretation: "Total payroll; limited to 50 row(s)",
        plan,
        result: {
          kind: "scalar",
          currency_by_column: { payroll: "USD" },
          columns: [{ key: "payroll", label: "Total payroll", format: "currency" }],
          rows: [{ payroll: "1000.00" }],
        },
      },
    };
    const action = vi
      .fn()
      .mockResolvedValueOnce(firstOutcome)
      .mockResolvedValueOnce({ status: "unavailable", message: "Stop after history check." });

    renderShell(action);
    act(() => openAskCompensation("What is the total payroll in Germany?"));

    await waitFor(() =>
      expect(action).toHaveBeenCalledWith("What is the total payroll in Germany?", []),
    );

    await userEvent.type(
      screen.getByRole("textbox", { name: "Question" }),
      "Convert that to INR.{Enter}",
    );

    await waitFor(() =>
      expect(action).toHaveBeenLastCalledWith("Convert that to INR.", [
        { question: "What is the total payroll in Germany?", plan },
      ]),
    );
  });
});
