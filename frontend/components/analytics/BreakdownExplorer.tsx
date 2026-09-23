"use client";

import { useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { TransitionLink } from "@/components/ui/RouteTransition";
import { analyticsHref, type AnalyticsMetric, type AnalyticsView } from "@/lib/api/analytics";
import { formatAmount, formatCount } from "@/lib/formatting/money";
import type { AnalyticsBreakdown, AnalyticsFilters, BreakdownRow, GroupBy } from "@/types/analytics";

export const DIMENSIONS: { key: GroupBy; label: string; plural: string }[] = [
  { key: "country", label: "Country", plural: "countries" },
  { key: "department", label: "Department", plural: "departments" },
  { key: "job_title", label: "Job title", plural: "job titles" },
];

export const METRICS: { key: AnalyticsMetric; label: string; short: string }[] = [
  { key: "payroll", label: "Total payroll", short: "Payroll" },
  { key: "average", label: "Average salary", short: "Average" },
  { key: "headcount", label: "Headcount", short: "Headcount" },
];

const INITIAL_ROWS = 12;

function magnitude(row: BreakdownRow, metric: AnalyticsMetric): number {
  const value =
    metric === "headcount" ? row.employee_count : Number(metric === "payroll" ? row.total_payroll_usd : row.average_salary_usd ?? 0);
  return Number.isFinite(value) ? value : 0;
}

/** Clicking a row focuses the page on it and breaks it down by the next dimension that is still open. */
function drillHref(filters: AnalyticsFilters, view: AnalyticsView, key: string): string {
  const next = { ...filters, [view.by]: key };
  const nextDimension = DIMENSIONS.find((dimension) => !next[dimension.key])?.key ?? view.by;
  return analyticsHref(next, { by: nextDimension, metric: view.metric });
}

function Money({ value, currency }: { value: string | null; currency: string }) {
  if (value === null) return <span className="text-ink-muted">—</span>;
  return <span title={`${value} ${currency}`}>{formatAmount(value, currency, { whole: true })}</span>;
}

function Segmented<T extends string>({
  label,
  items,
  current,
  href,
}: {
  label: string;
  items: { key: T; label: string }[];
  current: T;
  href: (key: T) => string;
}) {
  return (
    <nav aria-label={label} className="inline-flex rounded-control bg-surface-hover p-0.5">
      {items.map((item) => {
        const active = item.key === current;
        return (
          <TransitionLink
            key={item.key}
            href={href(item.key)}
            aria-current={active ? "true" : undefined}
            className={`flex h-7 items-center rounded-[5px] px-2.5 text-[13px] whitespace-nowrap transition-colors ${
              active
                ? "bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--color-border),0_1px_2px_rgb(17_24_39/0.06)]"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            {item.label}
          </TransitionLink>
        );
      })}
    </nav>
  );
}

interface BreakdownExplorerProps {
  breakdown: AnalyticsBreakdown;
  filters: AnalyticsFilters;
  view: AnalyticsView;
}

export function BreakdownExplorer({ breakdown, filters, view }: BreakdownExplorerProps) {
  const [expanded, setExpanded] = useState(false);
  const dimension = DIMENSIONS.find((item) => item.key === view.by) ?? DIMENSIONS[0];
  const metric = METRICS.find((item) => item.key === view.metric) ?? METRICS[0];
  const rows = breakdown.rows;
  const visible = expanded ? rows : rows.slice(0, INITIAL_ROWS);
  const max = rows.reduce((current, row) => Math.max(current, magnitude(row, view.metric)), 0);
  const currency = breakdown.currency;
  const focused = filters[view.by];
  const metricColumn = (key: AnalyticsMetric) =>
    key === view.metric ? "text-ink font-medium" : "text-ink-secondary";

  return (
    <section aria-labelledby="breakdown-heading" className="rounded-surface border border-border bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <h2 id="breakdown-heading" className="text-sm font-semibold text-ink">
            {metric.label} by {dimension.label.toLowerCase()}
          </h2>
          <p className="mt-0.5 text-xs text-ink-muted">
            Ranked highest first{view.metric === "headcount" ? "" : ` · ${currency}`} · Select a row to drill into it
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Segmented
            label="Break down by"
            items={DIMENSIONS}
            current={view.by}
            href={(key) => analyticsHref(filters, { by: key, metric: view.metric })}
          />
          <Segmented
            label="Measure"
            items={METRICS.map((item) => ({ key: item.key, label: item.short }))}
            current={view.metric}
            href={(key) => analyticsHref(filters, { by: view.by, metric: key })}
          />
        </div>
      </div>

      {focused && rows.length <= 1 && (
        <p className="border-b border-border bg-surface-muted px-4 py-2 text-xs text-ink-secondary">
          The page is filtered to {focused}, so this breakdown has a single row. Break it down by another dimension to compare.
        </p>
      )}

      <div className="@container">
        <table className="w-full text-[13px]">
          <caption className="sr-only">
            {metric.label} by {dimension.label.toLowerCase()}, ranked highest first
          </caption>
          <thead>
            <tr className="border-b border-border text-xs whitespace-nowrap text-ink-muted">
              <th scope="col" className="h-9 px-4 text-left font-medium">
                {dimension.label}
                <span className="float-right font-medium text-ink @2xl:hidden">{metric.label}</span>
              </th>
              <th scope="col" className="hidden w-[34%] px-2 text-left font-medium @2xl:table-cell">
                <span className="sr-only">{metric.label} bar</span>
              </th>
              <th scope="col" className={`hidden px-4 text-right font-medium @2xl:table-cell ${metricColumn("headcount")}`}>
                Employees
              </th>
              <th scope="col" className={`hidden px-4 text-right font-medium @2xl:table-cell ${metricColumn("payroll")}`}>
                Total payroll
              </th>
              <th scope="col" className={`hidden px-4 text-right font-medium @2xl:table-cell ${metricColumn("average")}`}>
                Average salary
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => {
              const width = max > 0 ? (magnitude(row, view.metric) / max) * 100 : 0;
              const selected = focused === row.key;
              const bar = (
                <span aria-hidden="true" className="block h-3 w-full">
                  <span
                    className={`block h-full rounded-r-[3px] transition-colors ${selected ? "bg-accent" : "bg-bar group-hover:bg-accent"}`}
                    style={{ width: `${Math.max(width, row.employee_count > 0 ? 0.75 : 0)}%` }}
                  />
                </span>
              );
              const metricValue =
                view.metric === "headcount" ? (
                  formatCount(row.employee_count)
                ) : (
                  <Money value={view.metric === "payroll" ? row.total_payroll_usd : row.average_salary_usd} currency={currency} />
                );
              return (
                <tr
                  key={row.key}
                  className={`group relative border-b border-border last:border-b-0 hover:bg-surface-muted has-[a:focus-visible]:bg-accent-soft/60 ${
                    selected ? "bg-accent-soft/50" : ""
                  }`}
                >
                  <th scope="row" className="h-10 max-w-0 px-4 py-2 text-left font-normal @2xl:w-[30%] @2xl:py-0">
                    <span className="flex items-center gap-2.5">
                      <span className="w-5 shrink-0 text-right text-xs tabular-nums text-ink-muted">{index + 1}</span>
                      <TransitionLink
                        href={drillHref(filters, view, row.key)}
                        className="truncate text-ink after:absolute after:inset-0 after:content-[''] group-hover:text-accent focus-visible:underline focus-visible:outline-none"
                        title={`Focus on ${row.key}`}
                      >
                        {row.key}
                      </TransitionLink>
                      <span className="ml-auto shrink-0 pl-3 tabular-nums font-medium text-ink @2xl:hidden">{metricValue}</span>
                    </span>
                    <span className="mt-1.5 block pl-7.5 @2xl:hidden">{bar}</span>
                  </th>
                  <td className="hidden px-2 @2xl:table-cell">{bar}</td>
                  <td className={`hidden px-4 text-right tabular-nums @2xl:table-cell ${metricColumn("headcount")}`}>
                    {formatCount(row.employee_count)}
                  </td>
                  <td className={`hidden px-4 text-right tabular-nums @2xl:table-cell ${metricColumn("payroll")}`}>
                    <Money value={row.total_payroll_usd} currency={currency} />
                  </td>
                  <td className={`hidden px-4 text-right tabular-nums @2xl:table-cell ${metricColumn("average")}`}>
                    <Money value={row.average_salary_usd} currency={currency} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {rows.length > INITIAL_ROWS && (
        <div className="border-t border-border px-4 py-2">
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            aria-expanded={expanded}
            className="inline-flex items-center gap-1 text-[13px] font-medium text-ink-secondary hover:text-ink"
          >
            {expanded ? "Show top " + INITIAL_ROWS : `Show all ${rows.length} ${dimension.plural}`}
            <Icon name="chevronDown" size={14} className={expanded ? "rotate-180" : ""} />
          </button>
        </div>
      )}
    </section>
  );
}
