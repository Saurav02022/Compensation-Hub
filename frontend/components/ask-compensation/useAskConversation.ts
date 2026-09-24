"use client";

import { useCallback, useRef, useState, useTransition } from "react";

import type { AskTurn } from "@/types/ask";
import { MAX_HISTORY_TURNS, MIN_QUESTION_LENGTH, type AskAction, type AskExchange } from "./types";

/**
 * The context a follow-up question is interpreted in: the latest answered questions with the
 * validated SQL and currency they used. Result figures are never sent back.
 */
export function conversationHistory(exchanges: AskExchange[]): AskTurn[] {
  const turns: AskTurn[] = [];
  for (const exchange of exchanges) {
    const { outcome } = exchange;
    if (outcome.status === "answered" && outcome.response.sql) {
      const { sql, currency } = outcome.response;
      turns.push({ question: exchange.question, sql, currency });
    }
  }
  return turns.slice(-MAX_HISTORY_TURNS);
}

/** Holds the conversation at the shell level so it survives navigation between pages. */
export function useAskConversation(action: AskAction) {
  const [exchanges, setExchanges] = useState<AskExchange[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const nextId = useRef(1);

  const ask = useCallback(
    (text: string): boolean => {
      const question = text.trim();
      if (question.length < MIN_QUESTION_LENGTH || pendingQuestion !== null) return false;
      const history = conversationHistory(exchanges);
      setPendingQuestion(question);
      startTransition(async () => {
        const outcome = await action(question, history);
        const id = nextId.current++;
        startTransition(() => {
          setExchanges((current) => [...current, { id, question, outcome }]);
          setPendingQuestion(null);
        });
      });
      return true;
    },
    [action, exchanges, pendingQuestion],
  );

  const reset = useCallback(() => setExchanges([]), []);

  return { exchanges, pendingQuestion, pending: pending || pendingQuestion !== null, ask, reset };
}
