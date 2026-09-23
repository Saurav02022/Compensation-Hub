import { MetricStrip } from "@/components/ui/Metric";
import { formatAmount, formatCount } from "@/lib/formatting/money";
import type { AnalyticsSummary } from "@/types/analytics";

interface SummaryMetricsProps {
  summary: AnalyticsSummary;
  /** Describes what the figures cover, e.g. "Whole organization" or "India · Engineering". */
  scope: string;
}

/** Headline figures rounded to whole units; the exact amount stays available on hover. */
export function SummaryMetrics({ summary, scope }: SummaryMetricsProps) {
  const { currency } = summary;
  return (
    <MetricStrip
      label="Compensation summary"
      items={[
        { label: "Employees", value: formatCount(summary.employee_count), note: scope },
        {
          label: "Total annual payroll",
          unit: currency,
          value: formatAmount(summary.total_payroll_usd, currency, { whole: true }),
          exact: `${summary.total_payroll_usd} ${currency}`,
          note: "Converted at fixed exchange rates",
        },
        {
          label: "Average annual salary",
          unit: summary.average_salary_usd === null ? undefined : currency,
          value: summary.average_salary_usd === null ? "—" : formatAmount(summary.average_salary_usd, currency, { whole: true }),
          exact: summary.average_salary_usd === null ? undefined : `${summary.average_salary_usd} ${currency}`,
          note: summary.average_salary_usd === null ? "No salaries to average" : "Per employee with a salary on record",
        },
      ]}
    />
  );
}

export function describeScope(filters: { country?: string; department?: string; job_title?: string }): string {
  const parts = [filters.country, filters.department, filters.job_title].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "Whole organization";
}
