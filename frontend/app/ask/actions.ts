"use server";

import type { AskFormState } from "@/components/ask-compensation/AskForm";
import { ApiError } from "@/lib/api/client";
import { askCompensation } from "@/lib/api/ask";

export async function askCompensationAction(
  _previous: AskFormState,
  formData: FormData,
): Promise<AskFormState> {
  const raw = formData.get("question");
  const question = typeof raw === "string" ? raw.trim() : "";

  try {
    return { status: "answered", response: await askCompensation(question) };
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
