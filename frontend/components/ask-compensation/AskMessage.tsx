import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { analyticsHref, type AnalyticsMetric } from "@/lib/api/analytics";
import { formatAmount, formatCount } from "@/lib/formatting/money";
import type { AskMetric, AskResultRow, QueryPlan } from "@/types/ask";
import type { AskExchange } from "./types";

const METRIC_LABELS: Record<AskMetric, string> = {
  employee_count: "Employee count",
  average_salary: "Average annual salary",
  total_payroll: "Total annual payroll",
};

const ANALYTICS_METRIC: Record<AskMetric, AnalyticsMetric> = {
  employee_count: "headcount",
  average_salary: "average",
  total_payroll: "payroll",
};

const DIMENSION_LABELS = { country: "country", department: "department", job_title: "job title" } as const;

/** A plain-language reading of the validated request, so the HR Manager can check the interpretation. */
export function describePlan(plan: QueryPlan): string {
  const parts: string[] = [METRIC_LABELS[plan.metric]];
  const filters = [plan.filters.country, plan.filters.department, plan.filters.job_title].filter(Boolean);
  if (plan.group_by) parts.push(`by ${DIMENSION_LABELS[plan.group_by]}`);
  if (filters.length > 0) parts.push(`for ${filters.join(", ")}`);
  if (plan.sort) parts.push(plan.sort === "desc" ? "highest first" : "lowest first");
  if (plan.limit) parts.push(`top ${plan.limit}`);
  return parts.join(", ");
}

function metricMagnitude(metric: AskMetric, row: AskResultRow): number {
  if (metric === "employee_count") return row.employee_count;
  const value = metric === "total_payroll" ? row.total_payroll_usd : row.average_salary_usd;
  const number = value === null ? 0 : Number(value);
  return Number.isFinite(number) ? number : 0;
}

function metricDisplay(metric: AskMetric, row: AskResultRow, currency: string): string {
  if (metric === "employee_count") return formatCount(row.employee_count);
  const value = metric === "total_payroll" ? row.total_payroll_usd : row.average_salary_usd;
  return value === null ? "—" : formatAmount(value, currency, { whole: true });
}

function analyticsLink(plan: QueryPlan): string {
  const filters = {
    country: plan.filters.country ?? undefined,
    department: plan.filters.department ?? undefined,
    job_title: plan.filters.job_title ?? undefined,
  };
  return analyticsHref(filters, { by: plan.group_by ?? undefined, metric: ANALYTICS_METRIC[plan.metric] });
}

function Unsupported({ answer }: { answer: string }) {
  return (
    <div role="status" className="rounded-surface border border-border bg-surface-muted px-3.5 py-3 text-[13px]">
      <p className="flex items-center gap-2 font-medium text-ink">
        <Icon name="info" className="text-ink-muted" />
        Can&apos;t answer this reliably
      </p>
      <p className="mt-1.5 text-ink-secondary">{answer}</p>
    </div>
  );
}

function Answer({ exchange }: { exchange: AskExchange }) {
  if (exchange.outcome.status !== "answered") return null;
  const { response } = exchange.outcome;
  const { plan, result } = response;

  if (response.status === "unsupported" || !plan || !result) {
    return <Unsupported answer={response.answer} />;
  }

  const grouped = plan.group_by !== null && result.rows.length > 0;
  const currencyUnit = plan.metric === "employee_count" ? null : result.currency;
  const max = result.rows.reduce((current, row) => Math.max(current, metricMagnitude(plan.metric, row)), 0);

  return (
    <div className="rounded-surface border border-border bg-surface px-3.5 py-3">
      {grouped ? (
        <>
          <p className="text-[13px] font-medium text-ink">
            {METRIC_LABELS[plan.metric]} by {plan.group_by && DIMENSION_LABELS[plan.group_by]}
            {currencyUnit && <span className="font-normal text-ink-muted"> · {currencyUnit}</span>}
          </p>
          <table className="mt-2 w-full table-fixed text-[13px]">
            <caption className="sr-only">{response.answer}</caption>
            <thead className="sr-only">
              <tr>
                <th scope="col">{plan.group_by && DIMENSION_LABELS[plan.group_by]}</th>
                <th scope="col">{METRIC_LABELS[plan.metric]}</th>
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row) => {
                const width = max > 0 ? (metricMagnitude(plan.metric, row) / max) * 100 : 0;
                return (
                  <tr key={row.key ?? ""}>
                    <th scope="row" className="w-[42%] truncate py-1 pr-3 text-left font-normal text-ink">
                      {row.key}
                    </th>
                    <td className="py-1">
                      <span className="flex items-center gap-2">
                        <span aria-hidden="true" className="h-2 min-w-0 flex-1">
                          <span className="block h-full rounded-r-[3px] bg-bar" style={{ width: `${width}%` }} />
                        </span>
                        <span className="w-[5.5rem] shrink-0 text-right tabular-nums text-ink">
                          {metricDisplay(plan.metric, row, result.currency)}
                        </span>
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      ) : (
        <>
          <p className="flex items-baseline gap-1.5">
            {currencyUnit && <span className="text-[13px] font-medium text-ink-muted">{currencyUnit}</span>}
            <span className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-ink">
              {result.rows[0] ? metricDisplay(plan.metric, result.rows[0], result.currency) : "—"}
            </span>
          </p>
          <p className="mt-1 text-[13px] text-ink-secondary">{response.answer}</p>
        </>
      )}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-border pt-2 text-xs">
        <p className="text-ink-muted">Read as: {describePlan(plan)}</p>
        <Link
          href={analyticsLink(plan)}
          className="inline-flex items-center gap-1 font-medium text-accent hover:text-accent-hover hover:underline"
        >
          Open in Analytics
          <Icon name="arrowRight" size={13} />
        </Link>
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
