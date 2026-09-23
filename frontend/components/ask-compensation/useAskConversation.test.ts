import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AskResponse, AskTurn } from "@/types/ask";
import { MAX_HISTORY_TURNS, type AskExchange, type AskOutcome } from "./types";
import { conversationHistory, useAskConversation } from "./useAskConversation";

function answered(question: string, query: Record<string, unknown> | null): AskOutcome {
  const response: AskResponse = {
    status: query ? "answered" : "missing_data",
    question,
    answer: "",
    interpretation: null,
    missing: [],
    query,
    result: null,
    analytics_view: null,
  };
  return { status: "answered", response };
}

describe("conversationHistory", () => {
  it("keeps only answered questions with their queries, latest last, within the bound", () => {
    const exchanges: AskExchange[] = [
      ...Array.from({ length: MAX_HISTORY_TURNS + 1 }, (_, index) => ({
        id: index,
        question: `Question ${index}`,
        outcome: answered(`Question ${index}`, { kind: "aggregate", turn: index }),
      })),
      { id: 90, question: "Male engineers?", outcome: answered("Male engineers?", null) },
      { id: 91, question: "Down?", outcome: { status: "unavailable", message: "Down." } },
    ];

    const history = conversationHistory(exchanges);

    expect(history).toHaveLength(MAX_HISTORY_TURNS);
    expect(history[0].question).toBe("Question 1");
    expect(history.at(-1)).toEqual({ question: `Question ${MAX_HISTORY_TURNS}`, query: { kind: "aggregate", turn: MAX_HISTORY_TURNS } });
  });
});

describe("useAskConversation", () => {
  it("sends each follow-up with the earlier validated queries", async () => {
    const action = vi.fn(async (question: string, history: AskTurn[]): Promise<AskOutcome> => {
      void history;
      return answered(question, { kind: "aggregate", question });
    });
    const { result } = renderHook(() => useAskConversation(action));

    act(() => {
      result.current.ask("What is the total payroll in Germany?");
    });
    await waitFor(() => expect(result.current.exchanges).toHaveLength(1));
    act(() => {
      result.current.ask("Convert that to INR.");
    });
    await waitFor(() => expect(result.current.exchanges).toHaveLength(2));

    expect(action).toHaveBeenNthCalledWith(1, "What is the total payroll in Germany?", []);
    expect(action).toHaveBeenNthCalledWith(2, "Convert that to INR.", [
      {
        question: "What is the total payroll in Germany?",
        query: { kind: "aggregate", question: "What is the total payroll in Germany?" },
      },
    ]);

    act(() => result.current.reset());
    act(() => {
      result.current.ask("And India?");
    });
    await waitFor(() => expect(action).toHaveBeenCalledTimes(3));
    expect(action).toHaveBeenLastCalledWith("And India?", []);
  });
});
