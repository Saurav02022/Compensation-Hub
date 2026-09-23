import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse, QueryProgram } from "@/types/ask";
import type { AskAction } from "./types";
import { useAskConversation } from "./useAskConversation";

const plan: QueryProgram = {
  queries: [
    {
      name: "answer",
      select: [{ alias: "total_payroll", field: "salary_usd", aggregate: "sum" }],
      filters: [{ field: "country", op: "eq", values: ["Germany"] }],
      group_by: [],
      order_by: [],
      distinct: false,
      limit: null,
      target_currency: null,
    },
  ],
  calculation: null,
};

function response(question: string, responsePlan: QueryProgram): AskResponse {
  return {
    status: "answered",
    question,
    answer: "Total Payroll: USD 100.00.",
    interpretation: "sum salary usd where country eq Germany",
    plan: responsePlan,
    result: {
      kind: "scalar",
      currency: "USD",
      columns: [{ key: "total_payroll", label: "Total Payroll", format: "currency" }],
      rows: [{ total_payroll: "100.00" }],
    },
    analytics_path: "/analytics?country=Germany&metric=payroll",
  };
}

describe("useAskConversation", () => {
  it("passes prior validated programs to a follow-up without sending prior result rows", async () => {
    const firstQuestion = "What is the total payroll in Germany?";
    const followUp = "Convert that to Indian currency.";
    const convertedPlan: QueryProgram = {
      queries: [{ ...plan.queries[0], target_currency: "INR" }],
      calculation: null,
    };
    const action = vi.fn<AskAction>(async (question) => ({
      status: "answered",
      response: response(question, question === firstQuestion ? plan : convertedPlan),
    }));
    const { result } = renderHook(() => useAskConversation(action));

    act(() => {
      expect(result.current.ask(firstQuestion)).toBe(true);
    });
    await waitFor(() => expect(result.current.exchanges).toHaveLength(1));

    act(() => {
      expect(result.current.ask(followUp)).toBe(true);
    });
    await waitFor(() => expect(result.current.exchanges).toHaveLength(2));

    expect(action).toHaveBeenNthCalledWith(1, firstQuestion, []);
    expect(action).toHaveBeenNthCalledWith(2, followUp, [
      { question: firstQuestion, plan },
    ]);

    const history = action.mock.calls[1][1];
    expect(JSON.stringify(history)).not.toContain("100.00");
  });

  it("does not place unsupported answers into follow-up context", async () => {
    const missingQuestion = "How many male engineers are in India?";
    const followUp = "What about Germany?";
    const action = vi.fn<AskAction>(async (question) => {
      if (question === missingQuestion) {
        return {
          status: "answered",
          response: {
            status: "unsupported",
            question,
            answer:
              "I can't answer that from the data available in Compensation Hub. Gender is not stored for employees.",
            interpretation: null,
            plan: null,
            result: null,
            analytics_path: null,
          },
        };
      }
      return { status: "unavailable", message: "Not configured." };
    });
    const { result } = renderHook(() => useAskConversation(action));

    act(() => {
      expect(result.current.ask(missingQuestion)).toBe(true);
    });
    await waitFor(() => expect(result.current.exchanges).toHaveLength(1));

    act(() => {
      expect(result.current.ask(followUp)).toBe(true);
    });
    await waitFor(() => expect(action).toHaveBeenCalledTimes(2));

    expect(action).toHaveBeenNthCalledWith(2, followUp, []);
  });
});
