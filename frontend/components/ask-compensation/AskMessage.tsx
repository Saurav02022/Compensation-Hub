import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { analyticsHref } from "@/lib/api/analytics";
import { formatAmount, formatCount, formatSalary } from "@/lib/formatting/money";
import type { AskAnalyticsView, AskResponse, AskResult, ResultColumn, ResultRow, ResultValue } from "@/types/ask";
import type { AskExchange } from "./types";

const NUMERIC_TYPES = new Set(["count", "money", "percent", "number"]);

function formatNumber(value: ResultValue, fractionDigits: number): string {
  const number = Number(value);
  return Number.isFinite(number)
    ? number.toLocaleString("en-US", { maximumFractionDigits: fractionDigits })
    : String(value);
}

/** Presentation only: every figure arrives computed and rounded by the backend. */
export function formatCell(value: ResultValue, column: ResultColumn, row: ResultRow, columns: ResultColumn[]): string {
  if (value === null) return "—";
  switch (column.type) {
    case "count":
      return formatCount(Number(value));
    case "percent":
      return `${formatNumber(value, 2)}%`;
    case "number":
      return formatNumber(value, 2);
    case "money": {
      if (column.currency) return formatAmount(String(value), column.currency);
      const currencyIndex = columns.findIndex((candidate) => candidate.key === column.currency_key);
      const currency = currencyIndex >= 0 ? row.values[currencyIndex] : null;
      return currency ? formatSalary(String(value), String(currency)) : String(value);
    }
    default:
      return String(value);
  }
}

function magnitude(value: ResultValue): number {
  const number = Number(value);
  return Number.isFinite(number) ? Math.abs(number) : 0;
}

function headerLabel(column: ResultColumn): string {
  return column.currency ? `${column.label} (${column.currency})` : column.label;
}

function analyticsLink(view: AskAnalyticsView): string {
  const filters = {
    country: view.country ?? undefined,
    department: view.department ?? undefined,
    job_title: view.job_title ?? undefined,
  };
  return analyticsHref(filters, { by: view.group_by ?? undefined, metric: view.metric });
}

function Scalar({ result }: { result: AskResult }) {
  const row = result.rows[0];
  const primaryIndex = Math.max(
    0,
    result.columns.findIndex((column) => column.key === result.primary),
  );
  const primary = result.columns[primaryIndex];
  const others = result.columns.map((column, index) => ({ column, index })).filter(({ index }) => index !== primaryIndex);

  return (
    <div>
      <p className="text-xs text-ink-muted">{primary.label}</p>
      <p className="mt-0.5 flex items-baseline gap-1.5">
        {primary.type === "money" && primary.currency && (
          <span className="text-[13px] font-medium text-ink-muted">{primary.currency}</span>
        )}
        <span className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-ink tabular-nums">
          {row ? formatCell(row.values[primaryIndex], primary, row, result.columns) : "—"}
        </span>
      </p>
      {row && others.length > 0 && (
        <dl className="mt-2.5 space-y-1 border-t border-border pt-2 text-xs">
          {others.map(({ column, index }) => (
            <div key={column.key} className="flex justify-between gap-3">
              <dt className="min-w-0 text-ink-secondary">{column.label}</dt>
              <dd className="shrink-0 text-right text-ink tabular-nums">
                {formatCell(row.values[index], column, row, result.columns)}
                {column.type === "money" && column.currency && <span className="text-ink-muted"> {column.currency}</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

function Table({ result, caption }: { result: AskResult; caption: string }) {
  // A column whose only job is to name another column's currency is shown inline instead.
  const hidden = new Set(result.columns.map((column) => column.currency_key).filter(Boolean));
  const visible = result.columns.map((column, index) => ({ column, index })).filter(({ column }) => !hidden.has(column.key));
  const textColumns = visible.filter(({ column }) => column.type === "text");
  const primaryIndex = result.columns.findIndex((column) => column.key === result.primary);
  // Bars only when the table is a single ranked comparison: one label and one figure.
  const showBars = primaryIndex >= 0 && textColumns.length === 1 && visible.length === 2;
  const max = showBars ? Math.max(0, ...result.rows.map((row) => magnitude(row.values[primaryIndex]))) : 0;
  const linkIndex = textColumns[0]?.index;

  if (result.rows.length === 0) {
    return <p className="text-[13px] text-ink-secondary">{caption}</p>;
  }

  return (
    <div className="-mx-3.5 overflow-x-auto px-3.5">
      <table className="w-full caption-bottom text-[13px]">
        <caption className="pt-2 text-left text-xs text-ink-muted">{caption}</caption>
        <thead>
          <tr className="border-b border-border text-left text-xs text-ink-muted">
            {visible.map(({ column }) => (
              <th
                key={column.key}
                scope="col"
                className={`py-1.5 pr-3 font-medium last:pr-0 ${NUMERIC_TYPES.has(column.type) ? "text-right" : ""}`}
              >
                {headerLabel(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, rowIndex) => (
            <tr key={row.employee_id ?? rowIndex} className="border-b border-border last:border-0">
              {visible.map(({ column, index }) => {
                const text = formatCell(row.values[index], column, row, result.columns);
                if (index === linkIndex) {
                  return (
                    <th key={column.key} scope="row" className="max-w-[12rem] truncate py-1.5 pr-3 text-left font-normal text-ink">
                      {row.employee_id !== null ? (
                        <Link href={`/employees/${row.employee_id}`} className="text-accent hover:underline">
                          {text}
                        </Link>
                      ) : (
                        text
                      )}
                    </th>
                  );
                }
                if (showBars && index === primaryIndex) {
                  const width = max > 0 ? (magnitude(row.values[index]) / max) * 100 : 0;
                  return (
                    <td key={column.key} className="w-1/2 py-1.5">
                      <span className="flex items-center gap-2">
                        <span aria-hidden="true" className="h-2 min-w-0 flex-1">
                          <span className="block h-full rounded-r-[3px] bg-bar" style={{ width: `${width}%` }} />
                        </span>
                        <span className="shrink-0 text-right tabular-nums text-ink">{text}</span>
                      </span>
                    </td>
                  );
                }
                return (
                  <td
                    key={column.key}
                    className={`py-1.5 pr-3 whitespace-nowrap last:pr-0 ${NUMERIC_TYPES.has(column.type) ? "text-right tabular-nums" : ""} text-ink`}
                  >
                    {text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NotAnswered({ response }: { response: AskResponse }) {
  const missing = response.status === "missing_data";
  return (
    <div role="status" className="rounded-surface border border-border bg-surface-muted px-3.5 py-3 text-[13px]">
      <p className="flex items-center gap-2 font-medium text-ink">
        <Icon name="info" className="text-ink-muted" />
        {missing ? "Not in the data" : "Can't answer this"}
      </p>
      <p className="mt-1.5 text-ink-secondary">{response.answer}</p>
    </div>
  );
}

function Answer({ response }: { response: AskResponse }) {
  const { result } = response;
  if (response.status !== "answered" || !result) {
    return <NotAnswered response={response} />;
  }

  return (
    <div className="rounded-surface border border-border bg-surface px-3.5 py-3">
      {result.kind === "scalar" ? <Scalar result={result} /> : <Table result={result} caption={response.answer} />}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-border pt-2 text-xs">
        {response.interpretation && <p className="min-w-0 text-ink-muted">Read as: {response.interpretation}</p>}
        {response.analytics_view && (
          <Link
            href={analyticsLink(response.analytics_view)}
            className="inline-flex items-center gap-1 font-medium text-accent hover:text-accent-hover hover:underline"
          >
            Open in Analytics
            <Icon name="arrowRight" size={13} />
          </Link>
        )}
      </div>
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
      <p className="ml-10 self-end rounded-surface bg-surface-hover px-3 py-2 text-[13px] text-ink">{question}</p>
      {outcome.status === "answered" && <Answer response={outcome.response} />}
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
