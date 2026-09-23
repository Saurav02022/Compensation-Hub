import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { formatAmount, formatCount } from "@/lib/formatting/money";
import type { AskResult, AskResultCell, AskResultColumn } from "@/types/ask";
import type { AskExchange } from "./types";

function displayCell(
  value: AskResultCell | undefined,
  column: AskResultColumn,
  result: AskResult,
): string {
  if (value === null || value === undefined || value === "") return "—";

  if (column.format === "count") {
    const number = typeof value === "number" ? value : Number(value);
    return Number.isFinite(number) ? formatCount(number) : String(value);
  }
  if (column.format === "currency") {
    const currency = result.currency ?? "USD";
    return `${currency} ${formatAmount(String(value), currency, { whole: true })}`;
  }
  if (column.format === "percent") return `${value}%`;
  return String(value);
}

function Unsupported({ answer }: { answer: string }) {
  return (
    <div role="status" className="rounded-surface border border-border bg-surface-muted px-3.5 py-3 text-[13px]">
      <p className="flex items-center gap-2 font-medium text-ink">
        <Icon name="info" className="text-ink-muted" />
        Can&apos;t answer this from the available data
      </p>
      <p className="mt-1.5 text-ink-secondary">{answer}</p>
    </div>
  );
}

function ScalarResult({ result }: { result: AskResult }) {
  const column = result.columns[0];
  const row = result.rows[0];
  if (!column || !row) return null;

  return (
    <p className="flex items-baseline gap-1.5">
      <span className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-ink">
        {displayCell(row[column.key], column, result)}
      </span>
    </p>
  );
}

function TableResult({ result }: { result: AskResult }) {
  return (
    <div className="mt-2 max-h-72 overflow-auto rounded-control border border-border">
      <table className="w-full text-left text-[12px]">
        <thead className="sticky top-0 bg-surface-muted text-ink-muted">
          <tr>
            {result.columns.map((column) => (
              <th key={column.key} scope="col" className="whitespace-nowrap px-2.5 py-2 font-medium">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {result.rows.map((row, index) => (
            <tr key={index}>
              {result.columns.map((column) => (
                <td key={column.key} className="whitespace-nowrap px-2.5 py-2 text-ink">
                  {displayCell(row[column.key], column, result)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmployeeResult({ result }: { result: AskResult }) {
  return (
    <ul className="mt-2 divide-y divide-border rounded-control border border-border">
      {result.rows.map((row, index) => (
        <li key={`${row.employee_code ?? index}`} className="px-3 py-2.5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-[13px] font-medium text-ink">{String(row.employee ?? "Employee")}</p>
              <p className="mt-0.5 truncate text-[11px] text-ink-muted">
                {[row.employee_code, row.role, row.country].filter(Boolean).join(" · ")}
              </p>
              {row.local_compensation && (
                <p className="mt-1 text-[11px] text-ink-secondary">
                  Local: {String(row.local_compensation)}
                </p>
              )}
            </div>
            {row.salary !== null && row.salary !== undefined && (
              <p className="shrink-0 text-right text-[12px] font-medium tabular-nums text-ink">
                {result.currency ?? "USD"}{" "}
                {formatAmount(String(row.salary), result.currency ?? "USD", { whole: true })}
              </p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Answer({ exchange }: { exchange: AskExchange }) {
  if (exchange.outcome.status !== "answered") return null;
  const { response } = exchange.outcome;

  if (response.status === "unsupported" || response.result === null) {
    return <Unsupported answer={response.answer} />;
  }

  return (
    <div className="rounded-surface border border-border bg-surface px-3.5 py-3">
      {response.result.kind === "scalar" && <ScalarResult result={response.result} />}
      {response.result.kind === "table" && <TableResult result={response.result} />}
      {response.result.kind === "employees" && <EmployeeResult result={response.result} />}

      <p className="mt-2 text-[13px] text-ink-secondary">{response.answer}</p>

      {(response.interpretation || response.analytics_path) && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-border pt-2 text-xs">
          {response.interpretation && (
            <p className="text-ink-muted">Read as: {response.interpretation}</p>
          )}
          {response.analytics_path && (
            <Link
              href={response.analytics_path}
              className="inline-flex items-center gap-1 font-medium text-accent hover:text-accent-hover hover:underline"
            >
              Open in Analytics
              <Icon name="arrowRight" size={13} />
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

interface AskMessageProps {
  exchange: AskExchange;
  onRetry: (question: string) => void;
}

export function AskMessage({ exchange, onRetry }: AskMessageProps) {
  const { question, outcome } = exchange;

  return (
    <article className="flex flex-col gap-2" aria-label={`Question: ${question}`}>
      <p className="ml-10 self-end rounded-surface bg-surface-hover px-3 py-2 text-[13px] text-ink">
        {question}
      </p>
      {outcome.status === "answered" && <Answer exchange={exchange} />}
      {outcome.status === "unavailable" && (
        <div
          role="alert"
          className="rounded-surface border border-warning-ink/15 bg-warning-soft px-3.5 py-3 text-[13px] text-warning-ink"
        >
          <p className="flex items-center gap-2 font-medium">
            <Icon name="alert" />
            Ask Compensation is unavailable
          </p>
          <p className="mt-1.5">{outcome.message}</p>
          <p className="mt-1.5 opacity-80">The directory, salary updates, and analytics keep working.</p>
        </div>
      )}
      {outcome.status === "error" && (
        <div
          role="alert"
          className="flex items-start justify-between gap-3 rounded-surface border border-negative-ink/15 bg-negative-soft px-3.5 py-3 text-[13px] text-negative-ink"
        >
          <p>{outcome.message}</p>
          <button
            type="button"
            onClick={() => onRetry(question)}
            className="shrink-0 font-medium underline-offset-2 hover:underline"
          >
            Retry
          </button>
        </div>
      )}
    </article>
  );
}
