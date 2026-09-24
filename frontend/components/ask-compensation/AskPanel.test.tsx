import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse } from "@/types/ask";
import { AskPanel, type AskConversation } from "./AskPanel";
import type { AskExchange } from "./types";

const share: AskResponse = {
  status: "answered",
  question: "What percentage of Engineering employees are in India?",
  answer: "Share in India: 18.86%; India employees: 656; Engineering employees: 3,478.",
  interpretation: "Counts Engineering employees and the share of them based in India.",
  missing: [],
  sql: "SELECT 1",
  currency: "USD",
  result: {
    kind: "scalar",
    columns: [
      { key: "india_employees", label: "India employees", type: "count", currency: null, currency_key: null },
      { key: "engineering_employees", label: "Engineering employees", type: "count", currency: null, currency_key: null },
      { key: "share_in_india", label: "Share in india", type: "percent", currency: null, currency_key: null },
    ],
    rows: [{ values: [656, 3478, "18.86"], employee_id: null }],
    primary: "share_in_india",
    total_rows: 1,
  },
  analytics_view: null,
};

const payroll: AskResponse = {
  status: "answered",
  question: "Total payroll in Germany?",
  answer: "Total payroll: USD 97,512,340.00. Amounts are in USD at the fixed exchange rates.",
  interpretation: "Sums the annual salaries of employees based in Germany.",
  missing: [],
  sql: "SELECT 1",
  currency: "USD",
  result: {
    kind: "scalar",
    columns: [{ key: "total_payroll", label: "Total payroll", type: "money", currency: "USD", currency_key: null }],
    rows: [{ values: ["97512340.00"], employee_id: null }],
    primary: "total_payroll",
    total_rows: 1,
  },
  analytics_view: { group_by: null, metric: "payroll", country: "Germany", department: null, job_title: null },
};

const topEarners: AskResponse = {
  status: "answered",
  question: "Who are the highest-paid employees in Germany?",
  answer: "Showing the first 2 of 1,003 results. Amounts are in USD at the fixed exchange rates.",
  interpretation: "Lists employees in Germany from the highest salary down.",
  missing: [],
  sql: "SELECT 1",
  currency: "USD",
  result: {
    kind: "table",
    columns: [
      { key: "full_name", label: "Name", type: "text", currency: null, currency_key: null },
      { key: "salary_local", label: "Local salary", type: "money", currency: null, currency_key: "salary_currency" },
      { key: "salary_currency", label: "Currency", type: "text", currency: null, currency_key: null },
      { key: "salary_usd", label: "Salary", type: "money", currency: "USD", currency_key: null },
    ],
    rows: [
      { values: ["Mia Weber", "231500.00", "EUR", "250020.00"], employee_id: 42 },
      { values: ["Jonas Fischer", "229000.00", "EUR", "247320.00"], employee_id: 7 },
    ],
    primary: null,
    total_rows: 1003,
  },
  analytics_view: null,
};

const byDepartment: AskResponse = {
  status: "answered",
  question: "Payroll by department",
  answer: "2 results. Amounts are in USD at the fixed exchange rates.",
  interpretation: "Sums annual salaries for each department.",
  missing: [],
  sql: "SELECT 1",
  currency: "USD",
  result: {
    kind: "table",
    columns: [
      { key: "department", label: "Department", type: "text", currency: null, currency_key: null },
      { key: "total_payroll", label: "Total payroll", type: "money", currency: "USD", currency_key: null },
    ],
    rows: [
      { values: ["Engineering", "397287000.00"], employee_id: null },
      { values: ["Sales", "113502000.00"], employee_id: null },
      { values: ["Research", null], employee_id: null },
    ],
    primary: "total_payroll",
    total_rows: 3,
  },
  analytics_view: { group_by: "department", metric: "payroll", country: null, department: null, job_title: null },
};

function conversation(overrides: Partial<AskConversation> = {}): AskConversation {
  return { exchanges: [], pendingQuestion: null, pending: false, ask: vi.fn(() => true), reset: vi.fn(), ...overrides };
}

function answered(id: number, response: AskResponse): AskExchange {
  return { id, question: response.question, outcome: { status: "answered", response } };
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
      suggestions={["Which department has the largest payroll?"]}
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

    await userEvent.click(screen.getByRole("button", { name: "Which department has the largest payroll?" }));
    expect(value.ask).toHaveBeenCalledWith("Which department has the largest payroll?");

    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox", { name: "Question" }), "How many employees are in India?{Enter}");
    expect(value.ask).toHaveBeenLastCalledWith("How many employees are in India?");
  });

  it("shows the pending question while the answer is worked out", () => {
    renderPanel({ conversation: conversation({ pendingQuestion: "Total payroll in Germany?", pending: true }) });

    expect(screen.getByText("Total payroll in Germany?")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Working out the answer");
  });

  it("renders a scalar answer from its columns, headline first, with the reading of the query", () => {
    renderPanel({ conversation: conversation({ exchanges: [answered(1, share), answered(2, payroll)] }) });

    const [shareAnswer, payrollAnswer] = screen.getAllByRole("article");
    expect(within(shareAnswer).getByText("18.86%")).toBeInTheDocument();
    expect(within(shareAnswer).getByText("656")).toBeInTheDocument();
    expect(within(shareAnswer).getByText("3,478")).toBeInTheDocument();
    expect(within(shareAnswer).getByText(/^Read as: /)).toHaveTextContent("share of them based in India");
    expect(within(shareAnswer).queryByRole("link", { name: /Open in Analytics/ })).not.toBeInTheDocument();

    expect(within(payrollAnswer).getByText("97,512,340.00")).toBeInTheDocument();
    expect(within(payrollAnswer).getByRole("link", { name: /Open in Analytics/ })).toHaveAttribute(
      "href",
      "/analytics?country=Germany",
    );
  });

  it("renders employee rows with local currency inline and links to each employee", () => {
    renderPanel({ conversation: conversation({ exchanges: [answered(1, topEarners)] }) });

    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "Name",
      "Local salary",
      "Salary (USD)",
    ]);
    expect(within(table).getByRole("link", { name: "Mia Weber" })).toHaveAttribute("href", "/employees/42");
    expect(within(table).getByText("EUR 231,500.00")).toBeInTheDocument();
    expect(within(table).getByText("250,020.00")).toBeInTheDocument();
    expect(screen.getByText("Showing the first 2 of 1,003 results. Amounts are in USD at the fixed exchange rates.")).toBeInTheDocument();
  });

  it("renders grouped results with bars and a link to the matching Analytics view", () => {
    renderPanel({ conversation: conversation({ exchanges: [answered(1, byDepartment)] }) });

    expect(screen.getByRole("rowheader", { name: "Engineering" })).toBeInTheDocument();
    expect(screen.getByText("397,287,000.00")).toBeInTheDocument();
    // A missing figure is shown as a dash, never as zero.
    expect(within(screen.getByRole("row", { name: /Research/ })).getByText("—")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open in Analytics/ })).toHaveAttribute("href", "/analytics?by=department");
  });

  it("distinguishes missing data, unsupported questions, an unavailable provider, and retryable errors", async () => {
    const missing: AskResponse = {
      status: "missing_data",
      question: "How many male engineers are in India?",
      answer: "This needs data Compensation Hub does not store: gender.",
      interpretation: null,
      missing: ["gender"],
      sql: null,
      currency: "USD",
      result: null,
      analytics_view: null,
    };
    const unsupported: AskResponse = { ...missing, status: "unsupported", question: "Who deserves a raise?", answer: "Salary recommendations are not made.", missing: [] };
    const value = conversation({
      exchanges: [
        answered(1, missing),
        answered(2, unsupported),
        { id: 3, question: "How many employees?", outcome: { status: "unavailable", message: "Provider is down." } },
        { id: 4, question: "Average in Sales?", outcome: { status: "error", message: "The question could not be sent." } },
      ],
    });
    renderPanel({ conversation: value });

    expect(screen.getByText("Not in the data")).toBeInTheDocument();
    expect(screen.getByText("This needs data Compensation Hub does not store: gender.")).toBeInTheDocument();
    expect(screen.getByText("Can't answer this")).toBeInTheDocument();
    expect(screen.getByText("Salary recommendations are not made.")).toBeInTheDocument();
    const alerts = screen.getAllByRole("alert");
    expect(alerts[0]).toHaveTextContent("Ask Compensation is unavailable");
    expect(alerts[0]).toHaveTextContent("The directory, salary updates, and analytics keep working.");

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(value.ask).toHaveBeenCalledWith("Average in Sales?");
  });
});
