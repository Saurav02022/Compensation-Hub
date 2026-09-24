import type { AskResponse, AskTurn } from "@/types/ask";

export type AskOutcome =
  | { status: "answered"; response: AskResponse }
  | { status: "unavailable"; message: string }
  | { status: "error"; message: string };

export type AskAction = (question: string, history: AskTurn[]) => Promise<AskOutcome>;

export interface AskExchange {
  id: number;
  question: string;
  outcome: AskOutcome;
}

export const MIN_QUESTION_LENGTH = 3;

/** Follow-ups carry this many earlier answered questions; the API rejects longer histories. */
export const MAX_HISTORY_TURNS = 4;
