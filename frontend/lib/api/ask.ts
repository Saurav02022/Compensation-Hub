import type { AskResponse, AskTurn } from "@/types/ask";
import { apiFetch } from "./client";

export function askCompensation(question: string, history: AskTurn[]): Promise<AskResponse> {
  return apiFetch<AskResponse>("/analytics/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
}
