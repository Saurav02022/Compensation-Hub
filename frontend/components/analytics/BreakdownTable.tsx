import { formatSalary } from "@/lib/formatting/money";
import type { AnalyticsBreakdown } from "@/types/analytics";

const DIMENSION_LABELS = {
  country: "Country",
  department: "Department",
  job_title: "Job title",
} as const;

interface BreakdownTableProps {
  breakdown: AnalyticsBreakdown;
  caption: string;
}

const HEADER_CELL = "px-3 py-2 text-xs font-medium text-ink-secondary";

export function BreakdownTable({ breakdown, caption }: BreakdownTableProps) {
  const dimension = DIMENSION_LABELS[breakdown.group_by];

  if (breakdown.rows.length === 0) {
    return (
      <p role="status" className="px-3 py-4 text-sm text-ink-secondary">
        No employees match the current filters.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-border bg-surface-muted text-left">
          <tr>
            <th scope="col" className={HEADER_CELL}>{dimension}</th>
            <th scope="col" className={`${HEADER_CELL} text-right`}>Employees</th>
            <th scope="col" className={`${HEADER_CELL} text-right`}>Total payroll ({breakdown.currency})</th>
            <th scope="col" className={`${HEADER_CELL} text-right`}>Average salary ({breakdown.currency})</th>
          </tr>
        </thead>
        <tbody>
          {breakdown.rows.map((row) => (
            <tr key={row.key} className="border-b border-border last:border-b-0">
              <th scope="row" className="px-3 py-2 text-left font-normal text-ink">
                {row.key}
              </th>
              <td className="px-3 py-2 text-right tabular-nums text-ink">{row.employee_count.toLocaleString("en-US")}</td>
              <td className="px-3 py-2 text-right tabular-nums text-ink">{formatSalary(row.total_payroll_usd, breakdown.currency)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-ink">
                {row.average_salary_usd === null ? "—" : formatSalary(row.average_salary_usd, breakdown.currency)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
