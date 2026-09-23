import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse, QueryPlan } from "@/types/ask";
import type { AskAction } from "./types";
import { useAskConversation } from "./useAskConversation";

const plan: QueryPlan = {
  kind: "aggregate",
  metric: "total_payroll",
  filters: {
    countries: ["Germany"],
    departments: [],
    job_titles: [],
    currency_codes: [],
    employee_code: null,
    name_contains: null,
    salary_usd_min: null,
    salary_usd_max: null,
    has_compensation: null,
  },
  denominator_filters: null,
  compare_filters: null,
  group_by: null,
  field: null,
  sort: null,
  sort_by: null,
  limit: null,
  target_currency: null,
  comparison: null,
};

function response(question: string, responsePlan: QueryPlan): AskResponse {
  return {
    status: "answered",
    question,
    answer: "Total annual payroll for country Germany: USD 100.00.",
    interpretation: "Total annual payroll for country Germany",
    plan: responsePlan,
    result: {
      kind: "scalar",
      currency: "USD",
      columns: [{ key: "value", label: "Total annual payroll", format: "currency" }],
      rows: [{ value: "100.00" }],
    },
    analytics_path: "/analytics?country=Germany&metric=payroll",
  };
}

describe("useAskConversation", () => {
  it("passes prior validated plans to a follow-up without sending prior result rows", async () => {
    const firstQuestion = "What is the total payroll in Germany?";
    const followUp = "Convert that to Indian currency.";
    const convertedPlan: QueryPlan = { ...plan, target_currency: "INR" };
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
});
