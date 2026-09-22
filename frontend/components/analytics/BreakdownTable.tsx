import { formatSalary } from "@/lib/formatting/money";
import type { AnalyticsBreakdown } from "@/types/analytics";

const DIMENSION_LABELS = {
  country: "Country",
  department: "Department",
  job_title: "Job title",
} as const;

interface BreakdownTableProps {
  breakdown: AnalyticsBreakdown;
}

export function BreakdownTable({ breakdown }: BreakdownTableProps) {
  const dimension = DIMENSION_LABELS[breakdown.group_by];
  const headingId = `breakdown-${breakdown.group_by}`;

  return (
    <section aria-labelledby={headingId} className="space-y-2">
      <h2 id={headingId} className="text-lg font-semibold">
        By {dimension.toLowerCase()}
      </h2>
      {breakdown.rows.length === 0 ? (
        <p role="status" className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">
          No employees match the current filters.
        </p>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">{dimension}</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Employees</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">
                  Total payroll ({breakdown.currency})
                </th>
                <th scope="col" className="px-3 py-2 text-right font-medium">
                  Average salary ({breakdown.currency})
                </th>
              </tr>
            </thead>
            <tbody>
              {breakdown.rows.map((row) => (
                <tr key={row.key} className="border-t border-slate-200">
                  <th scope="row" className="px-3 py-2 text-left font-normal">
                    {row.key}
                  </th>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {row.employee_count.toLocaleString("en-US")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatSalary(row.total_payroll_usd, breakdown.currency)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {row.average_salary_usd === null
                      ? "—"
                      : formatSalary(row.average_salary_usd, breakdown.currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
