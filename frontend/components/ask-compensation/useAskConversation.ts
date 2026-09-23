"use client";

import { useCallback, useRef, useState, useTransition } from "react";

import type { AskHistoryItem } from "@/types/ask";
import { MIN_QUESTION_LENGTH, type AskAction, type AskExchange } from "./types";

function historyFrom(exchanges: AskExchange[]): AskHistoryItem[] {
  return exchanges
    .flatMap((exchange) => {
      if (
        exchange.outcome.status !== "answered" ||
        exchange.outcome.response.status !== "answered" ||
        exchange.outcome.response.plan === null
      ) {
        return [];
      }
      return [{ question: exchange.question, plan: exchange.outcome.response.plan }];
    })
    .slice(-6);
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

      const history = historyFrom(exchanges);
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
