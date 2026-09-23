import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse, QueryProgram } from "@/types/ask";
import { AskPanel, type AskConversation } from "./AskPanel";
import type { AskExchange } from "./types";

function program(): QueryProgram {
  return {
    queries: [
      {
        name: "answer",
        select: [{ alias: "employee_count", aggregate: "count" }],
        filters: [],
        group_by: [],
        order_by: [],
        distinct: false,
        limit: null,
        target_currency: null,
      },
    ],
    calculation: null,
  };
}

const scalar: AskResponse = {
  status: "answered",
  question: "How many Engineering employees are based in India?",
  answer: "Employee Count: 656.",
  interpretation: "Employee Count for country = India; department = Engineering",
  plan: {
    queries: [
      {
        name: "answer",
        select: [{ alias: "employee_count", aggregate: "count" }],
        filters: [
          { field: "country", op: "eq", values: ["India"] },
          { field: "department", op: "eq", values: ["Engineering"] },
        ],
        group_by: [],
        order_by: [],
        distinct: false,
        limit: null,
        target_currency: null,
      },
    ],
    calculation: null,
  },
  result: {
    kind: "scalar",
    currency: null,
    columns: [{ key: "employee_count", label: "Employee Count", format: "count" }],
    rows: [{ employee_count: 656 }],
  },
  analytics_path: "/analytics?metric=headcount&country=India&department=Engineering",
};

const table: AskResponse = {
  status: "answered",
  question: "Which departments have the highest average salary?",
  answer: "Derived 2 row(s) from Compensation Hub data.",
  interpretation: "Department, Average Salary, grouped by department",
  plan: {
    queries: [
      {
        name: "answer",
        select: [
          { alias: "department", field: "department" },
          { alias: "average_salary", field: "salary_usd", aggregate: "avg" },
        ],
        filters: [],
        group_by: ["department"],
        order_by: [{ key: "average_salary", direction: "desc" }],
        distinct: false,
        limit: null,
        target_currency: null,
      },
    ],
    calculation: null,
  },
  result: {
    kind: "table",
    currency: "USD",
    columns: [
      { key: "department", label: "Department", format: "text" },
      { key: "average_salary", label: "Average Salary", format: "currency" },
    ],
    rows: [
      { department: "Engineering", average_salary: "114228.50" },
      { department: "Sales", average_salary: "75067.60" },
    ],
  },
  analytics_path: null,
};

const employeeRows: AskResponse = {
  status: "answered",
  question: "Who are the two highest-paid employees in India?",
  answer: "Derived 2 row(s) from Compensation Hub data.",
  interpretation: "Employee, Employee Code, Salary for country = India",
  plan: {
    queries: [
      {
        name: "answer",
        select: [
          { alias: "employee", field: "full_name" },
          { alias: "employee_code", field: "employee_code" },
          { alias: "salary", field: "salary_usd" },
        ],
        filters: [{ field: "country", op: "eq", values: ["India"] }],
        group_by: [],
        order_by: [{ key: "salary", direction: "desc" }],
        distinct: false,
        limit: 2,
        target_currency: null,
      },
    ],
    calculation: null,
  },
  result: {
    kind: "table",
    currency: "USD",
    columns: [
      { key: "employee", label: "Employee", format: "text" },
      { key: "employee_code", label: "Employee Code", format: "text" },
      { key: "salary", label: "Salary", format: "currency" },
    ],
    rows: [
      { employee: "Aarav Sharma", employee_code: "EMP00001", salary: "95000.00" },
      { employee: "Isha Patel", employee_code: "EMP00002", salary: "89000.00" },
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
  it("opens as a labelled modal sheet and closes on Escape", async () => {
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

  it("asks suggested and typed questions", async () => {
    const { conversation: value } = renderPanel();

    await userEvent.click(screen.getByRole("button", { name: "What is the total payroll in Germany?" }));
    expect(value.ask).toHaveBeenCalledWith("What is the total payroll in Germany?");

    await userEvent.type(screen.getByRole("textbox", { name: "Question" }), "How many employees are in India?{Enter}");
    expect(value.ask).toHaveBeenLastCalledWith("How many employees are in India?");
  });

  it("shows the pending question while the answer is derived", () => {
    renderPanel({
      conversation: conversation({ pendingQuestion: "Total payroll in Germany?", pending: true }),
    });

    expect(screen.getByText("Total payroll in Germany?")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Working out the answer");
  });

  it("renders scalar and generic table answers", () => {
    const exchanges: AskExchange[] = [
      { id: 1, question: scalar.question, outcome: { status: "answered", response: scalar } },
      { id: 2, question: table.question, outcome: { status: "answered", response: table } },
      { id: 3, question: employeeRows.question, outcome: { status: "answered", response: employeeRows } },
    ];
    renderPanel({ conversation: conversation({ exchanges }) });

    expect(screen.getByText("656")).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.getByText("USD 114,229")).toBeInTheDocument();
    expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
    expect(screen.getByText("USD 95,000")).toBeInTheDocument();
    expect(screen.getByText("Read as: " + scalar.interpretation)).toBeInTheDocument();

    expect(screen.getByRole("link", { name: /Open in Analytics/ })).toHaveAttribute(
      "href",
      scalar.analytics_path,
    );
  });

  it("distinguishes missing data, provider outage, and retryable errors", async () => {
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
    expect(screen.getAllByRole("alert")[0]).toHaveTextContent("Ask Compensation is unavailable");

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(value.ask).toHaveBeenCalledWith("Average in Sales?");
  });

  it("accepts a valid generic program in conversation history", () => {
    const plan = program();
    expect(plan.queries[0].select[0].aggregate).toBe("count");
  });
});
