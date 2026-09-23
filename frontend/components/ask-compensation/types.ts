import type { AskResponse } from "@/types/ask";

export type AskOutcome =
  | { status: "answered"; response: AskResponse }
  | { status: "unavailable"; message: string }
  | { status: "error"; message: string };

export type AskAction = (question: string) => Promise<AskOutcome>;

export interface AskExchange {
  id: number;
  question: string;
  outcome: AskOutcome;
}

export const MIN_QUESTION_LENGTH = 3;
