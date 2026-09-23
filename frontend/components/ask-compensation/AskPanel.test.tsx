import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse } from "@/types/ask";
import { AskPanel, type AskConversation } from "./AskPanel";
import type { AskExchange } from "./types";

const grouped: AskResponse = {
  status: "answered",
  question: "Compare average salary by department.",
  answer: "Average annual salary by department across the organization: Engineering: USD 114,228.50.",
  plan: {
    metric: "average_salary",
    filters: { country: null, department: null, job_title: null },
    group_by: "department",
    sort: "desc",
    limit: null,
  },
  result: {
    currency: "USD",
    rows: [
      { key: "Engineering", employee_count: 3478, total_payroll_usd: "397287000.00", average_salary_usd: "114228.50" },
      { key: "Sales", employee_count: 1512, total_payroll_usd: "113502000.00", average_salary_usd: "75067.60" },
    ],
  },
};

const single: AskResponse = {
  status: "answered",
  question: "How many Engineering employees are based in India?",
  answer: "Employee count for country India, department Engineering: 656.",
  plan: {
    metric: "employee_count",
    filters: { country: "India", department: "Engineering", job_title: null },
    group_by: null,
    sort: null,
    limit: null,
  },
  result: {
    currency: "USD",
    rows: [{ key: null, employee_count: 656, total_payroll_usd: "29849880.00", average_salary_usd: "45503.00" }],
  },
};

function conversation(overrides: Partial<AskConversation> = {}): AskConversation {
  return { exchanges: [], pendingQuestion: null, pending: false, ask: vi.fn(() => true), reset: vi.fn(), ...overrides };
}

function renderPanel(options: { docked?: boolean; conversation?: AskConversation } = {}) {
  const onClose = vi.fn();
  const value = options.conversation ?? conversation();
  render(
    <AskPanel
      open
      docked={options.docked ?? false}
      onClose={onClose}
      conversation={value}
      suggestions={["Compare average salary by department."]}
      inputRef={createRef<HTMLTextAreaElement>()}
    />,
  );
  return { onClose, conversation: value };
}

describe("AskPanel", () => {
  it("opens as a labelled modal sheet on narrow screens, focusing the question and closing on Escape", async () => {
    const { onClose } = renderPanel();

    const dialog = screen.getByRole("dialog", { name: "Ask Compensation" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("textbox", { name: "Question" })).toHaveFocus();

    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("docks beside the page without blocking it on wide screens", async () => {
    const { onClose } = renderPanel({ docked: true });

    expect(screen.getByRole("dialog", { name: "Ask Compensation" })).not.toHaveAttribute("aria-modal");

    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("asks a suggested question, and a typed one with Enter", async () => {
    const { conversation: value } = renderPanel();

    await userEvent.click(screen.getByRole("button", { name: "Compare average salary by department." }));
    expect(value.ask).toHaveBeenCalledWith("Compare average salary by department.");

    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox", { name: "Question" }), "How many employees are in India?{Enter}");
    expect(value.ask).toHaveBeenLastCalledWith("How many employees are in India?");
  });

  it("shows the pending question while the answer is worked out", () => {
    renderPanel({ conversation: conversation({ pendingQuestion: "Total payroll in Germany?", pending: true }) });

    expect(screen.getByText("Total payroll in Germany?")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Working out the answer");
  });

  it("presents single and grouped answers with a plain reading and a link into Analytics", () => {
    const exchanges: AskExchange[] = [
      { id: 1, question: single.question, outcome: { status: "answered", response: single } },
      { id: 2, question: grouped.question, outcome: { status: "answered", response: grouped } },
    ];
    renderPanel({ conversation: conversation({ exchanges }) });

    expect(screen.getByText("656")).toBeInTheDocument();
    expect(screen.getByText(single.answer)).toBeInTheDocument();
    expect(screen.getByText("Read as: Employee count, for India, Engineering")).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Engineering" })).toBeInTheDocument();
    expect(screen.getByText("114,229")).toBeInTheDocument();

    const links = screen.getAllByRole("link", { name: /Open in Analytics/ });
    expect(links[0]).toHaveAttribute("href", "/analytics?country=India&department=Engineering&metric=headcount");
    expect(links[1]).toHaveAttribute("href", "/analytics?by=department&metric=average");
  });

  it("distinguishes unsupported questions, an unavailable provider, and errors that can be retried", async () => {
    const value = conversation({
      exchanges: [
        {
          id: 1,
          question: "Who deserves a raise?",
          outcome: {
            status: "answered",
            response: { status: "unsupported", question: "Who deserves a raise?", answer: "Salary recommendations are not supported.", plan: null, result: null },
          },
        },
        { id: 2, question: "How many employees?", outcome: { status: "unavailable", message: "Provider is down." } },
        { id: 3, question: "Average in Sales?", outcome: { status: "error", message: "The question could not be sent." } },
      ],
    });
    renderPanel({ conversation: value });

    expect(screen.getByText("Can't answer this reliably")).toBeInTheDocument();
    expect(screen.getByText("Salary recommendations are not supported.")).toBeInTheDocument();
    const alerts = screen.getAllByRole("alert");
    expect(alerts[0]).toHaveTextContent("Ask Compensation is unavailable");
    expect(alerts[0]).toHaveTextContent("The directory, salary updates, and analytics keep working.");

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(value.ask).toHaveBeenCalledWith("Average in Sales?");
  });
});
