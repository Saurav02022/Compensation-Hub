"use client";

import { useActionState } from "react";

import type { Compensation } from "@/types/employees";

export interface CompensationFormState {
  status: "idle" | "success" | "error";
  message: string;
}

export type CompensationFormAction = (
  previous: CompensationFormState,
  formData: FormData,
) => Promise<CompensationFormState>;

interface CompensationFormProps {
  action: CompensationFormAction;
  compensation: Compensation | null;
}

const initialState: CompensationFormState = { status: "idle", message: "" };

export function CompensationForm({ action, compensation }: CompensationFormProps) {
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <form action={formAction} className="mt-3 grid gap-3 md:grid-cols-3">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Annual salary</span>
        <input
          type="text"
          inputMode="decimal"
          name="annual_salary"
          required
          defaultValue={compensation?.annual_salary ?? ""}
          className="rounded border border-slate-300 px-2 py-1.5 tabular-nums"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Currency code</span>
        <input
          type="text"
          name="currency_code"
          required
          maxLength={3}
          autoCapitalize="characters"
          defaultValue={compensation?.currency_code ?? ""}
          className="rounded border border-slate-300 px-2 py-1.5 uppercase"
        />
      </label>
      <div className="flex items-end">
        <button
          type="submit"
          disabled={pending}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save compensation"}
        </button>
      </div>
      <p
        role={state.status === "error" ? "alert" : "status"}
        aria-live="polite"
        className={
          state.status === "error"
            ? "text-sm text-red-700 md:col-span-3"
            : "text-sm text-green-700 md:col-span-3"
        }
      >
        {state.message}
      </p>
    </form>
  );
}
