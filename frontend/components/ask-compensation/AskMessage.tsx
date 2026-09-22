import { formatSalary } from "@/lib/formatting/money";
import type { QueryPlan } from "@/types/ask";
import type { AskExchange } from "./AskDrawer";

const METRIC_LABELS = {
  employee_count: "Employee count",
  average_salary: "Average annual salary",
  total_payroll: "Total annual payroll",
} as const;

const DIMENSION_LABELS = {
  country: "Country",
  department: "Department",
  job_title: "Job title",
} as const;

function describePlan(plan: QueryPlan): string {
  const parts: string[] = [METRIC_LABELS[plan.metric]];
  const filters = [
    plan.filters.country && `country ${plan.filters.country}`,
    plan.filters.department && `department ${plan.filters.department}`,
    plan.filters.job_title && `job title ${plan.filters.job_title}`,
  ].filter(Boolean);
  if (filters.length > 0) parts.push(`for ${filters.join(", ")}`);
  if (plan.group_by) parts.push(`by ${DIMENSION_LABELS[plan.group_by].toLowerCase()}`);
  if (plan.sort) parts.push(plan.sort === "desc" ? "highest first" : "lowest first");
  if (plan.limit) parts.push(`top ${plan.limit}`);
  return parts.join(", ");
}

function metricValue(plan: QueryPlan, row: { employee_count: number; total_payroll_usd: string; average_salary_usd: string | null }, currency: string): string {
  if (plan.metric === "employee_count") return row.employee_count.toLocaleString("en-US");
  if (plan.metric === "total_payroll") return formatSalary(row.total_payroll_usd, currency);
  return row.average_salary_usd === null ? "—" : formatSalary(row.average_salary_usd, currency);
}

interface AskMessageProps {
  exchange: AskExchange;
}

export function AskMessage({ exchange }: AskMessageProps) {
  const { question, outcome } = exchange;

  return (
    <div className="space-y-2">
      <p className="ml-8 rounded-surface bg-accent-soft px-3 py-2 text-sm text-ink">{question}</p>
      {outcome.status === "answered" && outcome.response.status === "answered" && (
        <div className="mr-8 rounded-surface border border-border bg-surface-muted px-3 py-2 text-sm">
          <p className="text-ink">{outcome.response.answer}</p>
          {outcome.response.plan && (
            <p className="mt-1 text-xs text-ink-muted">Read as: {describePlan(outcome.response.plan)}</p>
          )}
          {outcome.response.plan?.group_by && outcome.response.result && outcome.response.result.rows.length > 0 && (
            <table className="mt-2 w-full text-xs">
              <thead className="text-ink-secondary">
                <tr>
                  <th scope="col" className="py-1 text-left font-medium">
                    {DIMENSION_LABELS[outcome.response.plan.group_by]}
                  </th>
                  <th scope="col" className="py-1 text-right font-medium">
                    {METRIC_LABELS[outcome.response.plan.metric]}
                  </th>
                </tr>
              </thead>
              <tbody>
                {outcome.response.result.rows.map((row) => (
                  <tr key={row.key ?? ""} className="border-t border-border">
                    <th scope="row" className="py-1 text-left font-normal text-ink">
                      {row.key}
                    </th>
                    <td className="py-1 text-right tabular-nums text-ink">
                      {metricValue(outcome.response.plan!, row, outcome.response.result!.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
      {outcome.status === "answered" && outcome.response.status === "unsupported" && (
        <div role="status" className="mr-8 rounded-surface border border-border bg-surface-muted px-3 py-2 text-sm">
          <p className="font-medium text-ink">Not supported</p>
          <p className="mt-1 text-ink-secondary">{outcome.response.answer}</p>
        </div>
      )}
      {outcome.status === "unavailable" && (
        <div role="alert" className="mr-8 rounded-surface border border-warning-ink/20 bg-warning-soft px-3 py-2 text-sm text-warning-ink">
          <p className="font-medium">Ask Compensation is unavailable</p>
          <p className="mt-1">{outcome.message}</p>
        </div>
      )}
      {outcome.status === "error" && (
        <p role="alert" className="mr-8 rounded-surface border border-negative-ink/20 bg-negative-soft px-3 py-2 text-sm text-negative-ink">
          {outcome.message}
        </p>
      )}
    </div>
  );
}
