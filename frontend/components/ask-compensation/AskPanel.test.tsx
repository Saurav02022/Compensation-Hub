import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse, QueryPlan } from "@/types/ask";
import { AskPanel, type AskConversation } from "./AskPanel";
import type { AskExchange } from "./types";

function countPlan(): QueryPlan {
  return {
    select: [
      {
        alias: "employee_count",
        label: "Employee count",
        format: "count",
        expression: { kind: "aggregate", function: "count" },
      },
    ],
    where: [
      { field: "country", operator: "equals", value: "India" },
      { field: "department", operator: "equals", value: "Engineering" },
    ],
    group_by: [],
    distinct: false,
    order_by: [],
    limit: 50,
  };
}

const scalar: AskResponse = {
  status: "answered",
  question: "How many Engineering employees are based in India?",
  answer: "Employee count: 656.",
  interpretation: "Employee count; with requested filters; limited to 50 row(s)",
  plan: countPlan(),
  result: {
    kind: "scalar",
    currency_by_column: {},
    columns: [{ key: "employee_count", label: "Employee count", format: "count" }],
    rows: [{ employee_count: 656 }],
  },
};

const table: AskResponse = {
  status: "answered",
  question: "Which departments have the highest average salary?",
  answer: "Found 2 row(s) from Compensation Hub data.",
  interpretation: "Department, Average salary; grouped by department; ordered by average_salary; limited to 50 row(s)",
  plan: {
    select: [
      {
        alias: "department",
        label: "Department",
        format: "text",
        expression: { kind: "field", field: "department" },
      },
      {
        alias: "average_salary",
        label: "Average salary",
        format: "currency",
        expression: {
          kind: "aggregate",
          function: "average",
          field: "salary_usd",
        },
      },
    ],
    where: [],
    group_by: ["department"],
    distinct: false,
    order_by: [{ key: "average_salary", direction: "desc" }],
    limit: 50,
  },
  result: {
    kind: "table",
    currency_by_column: { average_salary: "USD" },
    columns: [
      { key: "department", label: "Department", format: "text" },
      { key: "average_salary", label: "Average salary", format: "currency" },
    ],
    rows: [
      { department: "Engineering", average_salary: "114228.50" },
      { department: "Sales", average_salary: "75067.60" },
    ],
  },
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

  it("asks suggested and typed questions", async () => {
    const { conversation: value } = renderPanel();

    await userEvent.click(screen.getByRole("button", { name: "What is the total payroll in Germany?" }));
    expect(value.ask).toHaveBeenCalledWith("What is the total payroll in Germany?");

    await userEvent.type(screen.getByRole("textbox", { name: "Question" }), "What data do we have?{Enter}");
    expect(value.ask).toHaveBeenLastCalledWith("What data do we have?");
  });

  it("renders scalar and generic table answers", () => {
    const exchanges: AskExchange[] = [
      { id: 1, question: scalar.question, outcome: { status: "answered", response: scalar } },
      { id: 2, question: table.question, outcome: { status: "answered", response: table } },
    ];
    renderPanel({ conversation: conversation({ exchanges }) });

    expect(screen.getByText("656")).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.getByText("USD 114,229")).toBeInTheDocument();
    expect(screen.getByText("Read as: " + scalar.interpretation)).toBeInTheDocument();
  });

  it("distinguishes missing data, provider outage, and retryable errors", async () => {
    const value = conversation({
      exchanges: [
        {
          id: 1,
          question: "Ask for unavailable data",
          outcome: {
            status: "answered",
            response: {
              status: "unsupported",
              question: "Ask for unavailable data",
              answer:
                "I can't answer that from the data available in Compensation Hub. Missing data: The requested attribute is not stored.",
              interpretation: null,
              plan: null,
              result: null,
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
    expect(screen.getByText(/requested attribute is not stored/)).toBeInTheDocument();
    expect(screen.getAllByRole("alert")[0]).toHaveTextContent("Ask Compensation is unavailable");

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(value.ask).toHaveBeenCalledWith("Average in Sales?");
  });
});
