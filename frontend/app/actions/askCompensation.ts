"use server";

import type { AskOutcome } from "@/components/ask-compensation/types";
import { askCompensation } from "@/lib/api/ask";
import { ApiError } from "@/lib/api/client";
import type { AskTurn } from "@/types/ask";

export async function askCompensationAction(question: string, history: AskTurn[]): Promise<AskOutcome> {
  const trimmed = question.trim();
  try {
    return { status: "answered", response: await askCompensation(trimmed, history) };
  } catch (error) {
    if (error instanceof ApiError && error.status === 503) {
      return { status: "unavailable", message: error.message };
    }
    if (error instanceof ApiError && error.status === 422) {
      return { status: "error", message: error.message };
    }
    return {
      status: "error",
      message: "The question could not be sent because the API is unavailable. Try again.",
    };
  }
}
