import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse } from "@/types/ask";
import { AskForm, type AskFormState } from "./AskForm";

const answered: AskResponse = {
  status: "answered",
  question: "Show average compensation by department.",
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
    rows: [
      { key: "Engineering", employee_count: 3478, total_payroll_usd: "3478.00", average_salary_usd: "1.00" },
    ],
  },
};

async function submit(question: string) {
  const user = userEvent.setup();
  await user.type(screen.getByRole("textbox", { name: "Question" }), question);
  await user.click(screen.getByRole("button", { name: "Ask" }));
}

describe("AskForm", () => {
  it("submits the question and renders the answer with its grouped result", async () => {
    const action = vi.fn<(previous: AskFormState, formData: FormData) => Promise<AskFormState>>(
      async () => ({ status: "answered", response: answered }),
    );
    render(<AskForm action={action} exampleQuestions={["Example?"]} />);

    await submit("Show average compensation by department.");

    expect(action).toHaveBeenCalledTimes(1);
    expect(action.mock.calls[0][1].get("question")).toBe(
      "Show average compensation by department.",
    );
    expect(await screen.findByText(answered.answer)).toBeInTheDocument();
    expect(screen.getByText(/Interpreted as: Average annual salary, grouped by department/)).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Engineering" })).toBeInTheDocument();
    expect(screen.getByText("3,478")).toBeInTheDocument();
  });

  it("explains an unsupported question", async () => {
    const action = vi.fn(
      async (): Promise<AskFormState> => ({
        status: "answered",
        response: {
          status: "unsupported",
          question: "Who deserves a raise?",
          answer: "This question cannot be answered reliably.",
          plan: null,
          result: null,
        },
      }),
    );
    render(<AskForm action={action} exampleQuestions={[]} />);

    await submit("Who deserves a raise?");

    expect(await screen.findByText("This question is not supported")).toBeInTheDocument();
    expect(screen.getByText("This question cannot be answered reliably.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows the unavailable state when the provider is down", async () => {
    const action = vi.fn(
      async (): Promise<AskFormState> => ({
        status: "unavailable",
        message: "Ask Compensation is currently unavailable. Analytics continue to work.",
      }),
    );
    render(<AskForm action={action} exampleQuestions={[]} />);

    await submit("How many employees?");

    expect(await screen.findByRole("alert")).toHaveTextContent("Ask Compensation is unavailable");
    expect(screen.getByText(/Analytics continue to work/)).toBeInTheDocument();
  });
});
