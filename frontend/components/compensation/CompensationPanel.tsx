"use client";

import { useActionState, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Alert } from "@/components/ui/States";
import { formatAmount, formatSalary } from "@/lib/formatting/money";
import { currencyError, normalizeSalary, salaryError } from "@/lib/validation/compensation";
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

function currencyName(code: string): string | undefined {
  try {
    const name = new Intl.DisplayNames(["en"], { type: "currency" }).of(code);
    return name && name !== code ? name : undefined;
  } catch {
    return undefined;
  }
}

export function CompensationPanel({ action, compensation }: CompensationPanelProps) {
  const [editing, setEditing] = useState(compensation === null);
  const [salary, setSalary] = useState(compensation?.annual_salary ?? "");
  const [currency, setCurrency] = useState(compensation?.currency_code ?? "");
  const [errors, setErrors] = useState<{ salary?: string; currency?: string }>({});
  const [showSaved, setShowSaved] = useState(true);
  const editButtonRef = useRef<HTMLButtonElement>(null);
  const [state, formAction, pending] = useActionState(async (previous: CompensationFormState, formData: FormData) => {
    const next = await action(previous, formData);
    if (next.status === "success") {
      setEditing(false);
      setShowSaved(true);
      requestAnimationFrame(() => editButtonRef.current?.focus());
    }
    return next;
  }, initialState);
  const salaryId = useId();
  const currencyId = useId();

  function startEditing() {
    setSalary(compensation?.annual_salary ?? "");
    setCurrency(compensation?.currency_code ?? "");
    setErrors({});
    setShowSaved(false);
    setEditing(true);
  }

  function cancel() {
    setEditing(false);
    setErrors({});
    requestAnimationFrame(() => editButtonRef.current?.focus());
  }

  const normalizedSalary = normalizeSalary(salary);
  const nextCurrency = currency.trim().toUpperCase();
  const valid = !salaryError(salary) && !currencyError(currency);
  const differs =
    compensation !== null &&
    (Number(normalizedSalary) !== Number(compensation.annual_salary) || nextCurrency !== compensation.currency_code);
  const changed = valid && differs;
  // Invalid input keeps Save enabled so submitting explains what to fix; only a valid, unchanged value has nothing to save.
  const nothingToSave = compensation !== null && valid && !differs;
  const name = compensation ? currencyName(compensation.currency_code) : undefined;

  return (
    <section aria-labelledby="compensation-heading" className="rounded-surface border border-border bg-surface">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-border px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <h2 id="compensation-heading" className="text-sm font-semibold text-ink">
            Current compensation
          </h2>
          {state.status === "success" && !editing && showSaved && (
            <p role="status" className="flex animate-fade-in items-center gap-1 text-[13px] text-positive-ink">
              <Icon name="check" size={14} />
              {state.message}
            </p>
          )}
        </div>
        {!editing && (
          <Button ref={editButtonRef} size="sm" onClick={startEditing}>
            <Icon name="pencil" size={13} />
            {compensation ? "Edit salary" : "Add salary"}
          </Button>
        )}
      </div>

      <div className="px-4 py-4">
        {compensation ? (
          <dl>
            <dt className="text-[13px] text-ink-secondary">Annual salary</dt>
            <dd className="mt-1 flex items-baseline gap-2">
              <span className="text-[28px] leading-9 font-semibold tracking-[-0.02em] text-ink">
                {formatAmount(compensation.annual_salary, compensation.currency_code)}
              </span>
              <span className="text-sm font-medium text-ink-muted">{compensation.currency_code}</span>
            </dd>
            <dd className="mt-0.5 text-xs text-ink-muted">
              Paid in {name ? `${name} (${compensation.currency_code})` : compensation.currency_code}, the employee&apos;s
              local currency.
            </dd>
          </dl>
        ) : (
          !editing && <p className="text-[13px] text-ink-secondary">No compensation on record for this employee.</p>
        )}

        {editing && (
          <form
            action={formAction}
            noValidate
            onSubmit={(event) => {
              const nextErrors = { salary: salaryError(salary), currency: currencyError(currency) };
              setErrors(nextErrors);
              if (nextErrors.salary || nextErrors.currency) {
                event.preventDefault();
                document.getElementById(nextErrors.salary ? salaryId : currencyId)?.focus();
              }
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape" && compensation && !pending) {
                event.preventDefault();
                cancel();
              }
            }}
            className={`space-y-4 ${compensation ? "mt-5 border-t border-border pt-4" : ""}`}
          >
            {!compensation && (
              <p className="text-[13px] text-ink-secondary">No compensation on record yet. Add the current annual salary.</p>
            )}
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_7rem]">
              <Field
                label={compensation ? "New annual salary" : "Annual salary"}
                htmlFor={salaryId}
                hint="Up to two decimal places."
                error={errors.salary}
                errorId={`${salaryId}-error`}
              >
                <Input
                  id={salaryId}
                  name="annual_salary"
                  type="text"
                  inputMode="decimal"
                  autoComplete="off"
                  required
                  autoFocus
                  value={salary}
                  onChange={(event) => {
                    setSalary(event.target.value);
                    if (errors.salary) setErrors((current) => ({ ...current, salary: undefined }));
                  }}
                  aria-invalid={errors.salary ? true : undefined}
                  aria-describedby={errors.salary ? `${salaryId}-error` : undefined}
                  className="tabular-nums"
                />
              </Field>
              <Field
                label="Currency"
                htmlFor={currencyId}
                hint="Three-letter code."
                error={errors.currency}
                errorId={`${currencyId}-error`}
              >
                <Input
                  id={currencyId}
                  name="currency_code"
                  type="text"
                  required
                  maxLength={3}
                  autoCapitalize="characters"
                  autoComplete="off"
                  spellCheck={false}
                  value={currency}
                  onChange={(event) => {
                    setCurrency(event.target.value.toUpperCase());
                    if (errors.currency) setErrors((current) => ({ ...current, currency: undefined }));
                  }}
                  aria-invalid={errors.currency ? true : undefined}
                  aria-describedby={errors.currency ? `${currencyId}-error` : undefined}
                  className="uppercase"
                />
              </Field>
            </div>

            {compensation && (
              <div aria-live="polite" className="rounded-control bg-surface-muted px-3 py-2.5 text-[13px]">
                {changed ? (
                  <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-ink-muted">Change</span>
                    <span className="tabular-nums text-ink-secondary line-through decoration-ink-muted/50">
                      {formatSalary(compensation.annual_salary, compensation.currency_code)}
                    </span>
                    <Icon name="arrowRight" size={13} className="text-ink-muted" />
                    <span className="font-medium tabular-nums text-ink">{formatSalary(normalizedSalary, nextCurrency)}</span>
                  </p>
                ) : (
                  <p className="text-ink-muted">
                    Current salary {formatSalary(compensation.annual_salary, compensation.currency_code)}. Enter the new amount.
                  </p>
                )}
              </div>
            )}

            {state.status === "error" && <Alert tone="error" title="The salary was not saved">{state.message}</Alert>}

            <div className="flex items-center gap-2">
              <Button type="submit" variant="primary" disabled={pending || nothingToSave}>
                {pending ? "Saving…" : "Save salary"}
              </Button>
              {compensation && (
                <Button variant="ghost" onClick={cancel} disabled={pending}>
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
