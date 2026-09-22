"use client";

import { useActionState, useId, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { Alert } from "@/components/ui/States";
import { formatSalary } from "@/lib/formatting/money";
import type { Compensation } from "@/types/employees";

export interface CompensationFormState {
  status: "idle" | "success" | "error";
  message: string;
}

export type CompensationFormAction = (
  previous: CompensationFormState,
  formData: FormData,
) => Promise<CompensationFormState>;

interface CompensationPanelProps {
  action: CompensationFormAction;
  compensation: Compensation | null;
}

const initialState: CompensationFormState = { status: "idle", message: "" };

export function CompensationPanel({ action, compensation }: CompensationPanelProps) {
  const [editing, setEditing] = useState(compensation === null);
  const [state, formAction, pending] = useActionState(
    async (previous: CompensationFormState, formData: FormData) => {
      const next = await action(previous, formData);
      if (next.status === "success") setEditing(false);
      return next;
    },
    initialState,
  );
  const salaryId = useId();
  const currencyId = useId();

  return (
    <section aria-labelledby="compensation-heading" className="rounded-surface border border-border bg-surface">
      <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <h2 id="compensation-heading" className="text-base font-semibold text-ink">
            Current compensation
          </h2>
          <p className="mt-0.5 text-xs text-ink-muted">Annual salary in the employee&apos;s local currency.</p>
        </div>
        {!editing && (
          <Button onClick={() => setEditing(true)}>{compensation ? "Edit" : "Add compensation"}</Button>
        )}
      </div>

      <div className="space-y-4 px-4 py-4">
        {compensation ? (
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-ink-secondary">Annual salary</dt>
              <dd className="mt-1 text-2xl font-semibold tracking-tight text-ink tabular-nums">
                {formatSalary(compensation.annual_salary, compensation.currency_code)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-ink-secondary">Local currency</dt>
              <dd className="mt-1 text-2xl font-semibold tracking-tight text-ink">{compensation.currency_code}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-ink-secondary">No compensation on record for this employee.</p>
        )}

        {state.status === "success" && !editing && (
          <Alert tone="success">{state.message}</Alert>
        )}

        {editing && (
          <form action={formAction} className="space-y-3 rounded-surface border border-border bg-surface-muted p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Annual salary" htmlFor={salaryId} hint="Up to two decimal places, for example 65000.00">
                <Input
                  id={salaryId}
                  name="annual_salary"
                  type="text"
                  inputMode="decimal"
                  required
                  pattern="^\d+(\.\d{1,2})?$"
                  title="A positive amount with up to two decimal places"
                  defaultValue={compensation?.annual_salary ?? ""}
                  className="tabular-nums"
                />
              </Field>
              <Field label="Currency code" htmlFor={currencyId} hint="Three-letter code with a seeded exchange rate">
                <Input
                  id={currencyId}
                  name="currency_code"
                  type="text"
                  required
                  maxLength={3}
                  pattern="[A-Za-z]{3}"
                  title="A three-letter currency code"
                  autoCapitalize="characters"
                  defaultValue={compensation?.currency_code ?? ""}
                  className="uppercase"
                />
              </Field>
            </div>
            {state.status === "error" && <Alert tone="error">{state.message}</Alert>}
            <div className="flex items-center gap-2">
              <Button type="submit" variant="primary" disabled={pending}>
                {pending ? "Saving…" : "Save changes"}
              </Button>
              {compensation && (
                <Button variant="ghost" onClick={() => setEditing(false)} disabled={pending}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
