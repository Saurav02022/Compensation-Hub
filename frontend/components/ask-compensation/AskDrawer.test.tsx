import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse } from "@/types/ask";
import { AskDrawer, type AskExchange, type AskOutcome } from "./AskDrawer";

const answered: AskResponse = {
  status: "answered",
  question: "Compare average salary by department.",
  answer: "Average annual salary by department across the organization: Engineering: USD 1.00.",
  plan: {
    metric: "average_salary",
    filters: { country: null, department: null, job_title: null },
    group_by: "department",
    sort: null,
    limit: null,
  },
  result: {
    currency: "USD",
    rows: [{ key: "Engineering", employee_count: 3478, total_payroll_usd: "3478.00", average_salary_usd: "1.00" }],
  },
};

function renderDrawer(action: (question: string) => Promise<AskOutcome>, exchanges: AskExchange[] = []) {
  const onClose = vi.fn();
  const onExchange = vi.fn();
  render(
    <AskDrawer
      open
      onClose={onClose}
      action={action}
      exchanges={exchanges}
      onExchange={onExchange}
      suggestions={["Compare average salary by department."]}
    />,
  );
  return { onClose, onExchange };
}

describe("AskDrawer", () => {
  it("is a labelled dialog that focuses the question input and closes on Escape", async () => {
    const { onClose } = renderDrawer(vi.fn());

    const dialog = screen.getByRole("dialog", { name: "Ask Compensation" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("textbox", { name: "Question" })).toHaveFocus();

    await userEvent.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("sends a suggested question and reports the exchange", async () => {
    const action = vi.fn(async (): Promise<AskOutcome> => ({ status: "answered", response: answered }));
    const { onExchange } = renderDrawer(action);

    await userEvent.click(screen.getByRole("button", { name: "Compare average salary by department." }));

    await waitFor(() => expect(onExchange).toHaveBeenCalledTimes(1));
    expect(action).toHaveBeenCalledWith("Compare average salary by department.");
    expect(onExchange.mock.calls[0][0].outcome).toEqual({ status: "answered", response: answered });
  });

  it("sends a typed question with Enter and disables the button for short input", async () => {
    const action = vi.fn(async (): Promise<AskOutcome> => ({ status: "answered", response: answered }));
    renderDrawer(action);

    const input = screen.getByRole("textbox", { name: "Question" });
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
    await userEvent.type(input, "How many employees are in India?{Enter}");

    await waitFor(() => expect(action).toHaveBeenCalledWith("How many employees are in India?"));
  });

  it("renders answers, grouped results, unsupported, and unavailable exchanges", () => {
    renderDrawer(vi.fn(), [
      { id: 1, question: "Compare average salary by department.", outcome: { status: "answered", response: answered } },
      {
        id: 2,
        question: "Who deserves a raise?",
        outcome: {
          status: "answered",
          response: { status: "unsupported", question: "Who deserves a raise?", answer: "Cannot answer.", plan: null, result: null },
        },
      },
      { id: 3, question: "How many employees?", outcome: { status: "unavailable", message: "Provider is down." } },
    ]);

    expect(screen.getByText(answered.answer)).toBeInTheDocument();
    expect(screen.getByText(/Read as: Average annual salary, by department/)).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Engineering" })).toBeInTheDocument();
    expect(screen.getByText("Not supported")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Ask Compensation is unavailable");
    expect(screen.queryByRole("button", { name: "Compare average salary by department." })).not.toBeInTheDocument();
  });
});
