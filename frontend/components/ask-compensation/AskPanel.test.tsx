import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse, QueryFilters, QueryPlan } from "@/types/ask";
import { AskPanel, type AskConversation } from "./AskPanel";
import type { AskExchange } from "./types";

const EMPTY_FILTERS: QueryFilters = {
  countries: [],
  departments: [],
  job_titles: [],
  currency_codes: [],
  employee_code: null,
  name_contains: null,
  salary_usd_min: null,
  salary_usd_max: null,
  has_compensation: null,
};

function aggregatePlan(overrides: Partial<QueryPlan> = {}): QueryPlan {
  return {
    kind: "aggregate",
    metric: "employee_count",
    filters: EMPTY_FILTERS,
    denominator_filters: null,
    compare_filters: null,
    group_by: null,
    field: null,
    sort: null,
    sort_by: null,
    limit: null,
    target_currency: null,
    comparison: null,
    ...overrides,
  };
}

const grouped: AskResponse = {
  status: "answered",
  question: "Compare average salary by department.",
  answer: "Average annual salary by department for the organization. 2 result(s).",
  interpretation: "Average annual salary by department for the organization",
  plan: aggregatePlan({
    metric: "average_salary",
    group_by: "department",
    sort: "desc",
  }),
  result: {
    kind: "table",
    currency: "USD",
    columns: [
      { key: "key", label: "Department", format: "text" },
      { key: "value", label: "Average annual salary", format: "currency" },
    ],
    rows: [
      { key: "Engineering", value: "114228.50" },
      { key: "Sales", value: "75067.60" },
    ],
  },
  analytics_path: "/analytics?by=department&metric=average",
};

const single: AskResponse = {
  status: "answered",
  question: "How many Engineering employees are based in India?",
  answer: "Employee count for country India, department Engineering: 656.",
  interpretation: "Employee count for country India, department Engineering",
  plan: aggregatePlan({
    filters: {
      ...EMPTY_FILTERS,
      countries: ["India"],
      departments: ["Engineering"],
    },
  }),
  result: {
    kind: "scalar",
    currency: null,
    columns: [{ key: "value", label: "Employee count", format: "count" }],
    rows: [{ value: 656 }],
  },
  analytics_path: "/analytics?country=India&department=Engineering&metric=headcount",
};

const employees: AskResponse = {
  status: "answered",
  question: "Who are the two highest-paid engineers in India?",
  answer: "Found 12 matching employee(s). Showing 2.",
  interpretation: "Employees for country India, department Engineering, sorted by salary usd, first 2",
  plan: {
    ...aggregatePlan(),
    kind: "employees",
    metric: null,
    filters: {
      ...EMPTY_FILTERS,
      countries: ["India"],
      departments: ["Engineering"],
    },
    sort: "desc",
    sort_by: "salary_usd",
    limit: 2,
  },
  result: {
    kind: "employees",
    currency: "USD",
    columns: [
      { key: "employee", label: "Employee", format: "text" },
      { key: "employee_code", label: "Employee code", format: "text" },
      { key: "role", label: "Role", format: "text" },
      { key: "country", label: "Country", format: "text" },
      { key: "local_compensation", label: "Local compensation", format: "text" },
      { key: "salary", label: "Salary in USD", format: "currency" },
    ],
    rows: [
      {
        employee: "Aarav Sharma",
        employee_code: "EMP00001",
        role: "Software Engineer · Engineering",
        country: "India",
        local_compensation: "INR 8,000,000.00",
        salary: "95000.00",
      },
      {
        employee: "Isha Patel",
        employee_code: "EMP00002",
        role: "Senior Software Engineer · Engineering",
        country: "India",
        local_compensation: "INR 7,500,000.00",
        salary: "89000.00",
      },
    ],
  },
  analytics_path: null,
};

function conversation(overrides: Partial<AskConversation> = {}): AskConversation {
  return {
    exchanges: [],
    pendingQuestion: null,
    pending: false,
    ask: vi.fn(() => true),
    reset: vi.fn(),
    ...overrides,
  };
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
      suggestions={["What is the total payroll in Germany?"]}
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

    await userEvent.click(screen.getByRole("button", { name: "What is the total payroll in Germany?" }));
    expect(value.ask).toHaveBeenCalledWith("What is the total payroll in Germany?");

    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox", { name: "Question" }), "How many employees are in India?{Enter}");
    expect(value.ask).toHaveBeenLastCalledWith("How many employees are in India?");
  });

  it("shows the pending question while the answer is worked out", () => {
    renderPanel({
      conversation: conversation({ pendingQuestion: "Total payroll in Germany?", pending: true }),
    });

    expect(screen.getByText("Total payroll in Germany?")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Working out the answer");
  });

  it("presents scalar, table, and employee answers with the validated interpretation", () => {
    const exchanges: AskExchange[] = [
      { id: 1, question: single.question, outcome: { status: "answered", response: single } },
      { id: 2, question: grouped.question, outcome: { status: "answered", response: grouped } },
      { id: 3, question: employees.question, outcome: { status: "answered", response: employees } },
    ];
    renderPanel({ conversation: conversation({ exchanges }) });

    expect(screen.getByText("656")).toBeInTheDocument();
    expect(screen.getByText(single.answer)).toBeInTheDocument();
    expect(screen.getByText("Read as: " + single.interpretation)).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.getByText("USD 114,229")).toBeInTheDocument();
    expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
    expect(screen.getByText("INR 8,000,000.00")).toBeInTheDocument();

    const links = screen.getAllByRole("link", { name: /Open in Analytics/ });
    expect(links[0]).toHaveAttribute("href", single.analytics_path);
    expect(links[1]).toHaveAttribute("href", grouped.analytics_path);
  });

  it("distinguishes missing data, an unavailable provider, and errors that can be retried", async () => {
    const value = conversation({
      exchanges: [
        {
          id: 1,
          question: "How many male engineers are in India?",
          outcome: {
            status: "answered",
            response: {
              status: "unsupported",
              question: "How many male engineers are in India?",
              answer:
                "I can't answer that from the data available in Compensation Hub. Gender is not stored for employees.",
              interpretation: null,
              plan: null,
              result: null,
              analytics_path: null,
            },
          },
        },
        {
          id: 2,
          question: "How many employees?",
          outcome: { status: "unavailable", message: "Provider is down." },
        },
        {
          id: 3,
          question: "Average in Sales?",
          outcome: { status: "error", message: "The question could not be sent." },
        },
      ],
    });
    renderPanel({ conversation: value });

    expect(screen.getByText("Can't answer this from the available data")).toBeInTheDocument();
    expect(screen.getByText(/Gender is not stored/)).toBeInTheDocument();
    const alerts = screen.getAllByRole("alert");
    expect(alerts[0]).toHaveTextContent("Ask Compensation is unavailable");
    expect(alerts[0]).toHaveTextContent("The directory, salary updates, and analytics keep working.");

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(value.ask).toHaveBeenCalledWith("Average in Sales?");
  });
});
