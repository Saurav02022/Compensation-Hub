"use client";

import { useActionState } from "react";

import type { AskResponse } from "@/types/ask";
import { AskAnswer } from "./AskAnswer";

export type AskFormState =
  | { status: "idle" }
  | { status: "answered"; response: AskResponse }
  | { status: "unavailable"; message: string }
  | { status: "error"; message: string };

export type AskFormAction = (previous: AskFormState, formData: FormData) => Promise<AskFormState>;

interface AskFormProps {
  action: AskFormAction;
  exampleQuestions: string[];
}

const initialState: AskFormState = { status: "idle" };

export function AskForm({ action, exampleQuestions }: AskFormProps) {
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <div className="space-y-6">
      <form action={formAction} className="space-y-3 rounded border border-slate-200 bg-white p-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Question</span>
          <textarea
            name="question"
            required
            minLength={3}
            maxLength={500}
            rows={2}
            placeholder="For example: What is the average salary in Engineering?"
            className="rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={pending}
            className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-60"
          >
            {pending ? "Asking…" : "Ask"}
          </button>
          <span className="text-xs text-slate-500">Examples: {exampleQuestions.join(" · ")}</span>
        </div>
      </form>

      {pending && (
        <p role="status" className="text-sm text-slate-600">
          Working out the answer…
        </p>
      )}

      {!pending && state.status === "answered" && <AskAnswer response={state.response} />}

      {!pending && state.status === "unavailable" && (
        <div role="alert" className="rounded border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Ask Compensation is unavailable</p>
          <p className="mt-1">{state.message}</p>
        </div>
      )}

      {!pending && state.status === "error" && (
        <p role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {state.message}
        </p>
      )}
    </div>
  );
}
