import { formatSalary } from "@/lib/formatting/money";
import type { AskResponse, QueryPlan } from "@/types/ask";

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
    plan.filters.country && `country = ${plan.filters.country}`,
    plan.filters.department && `department = ${plan.filters.department}`,
    plan.filters.job_title && `job title = ${plan.filters.job_title}`,
  ].filter(Boolean);
  if (filters.length > 0) parts.push(`where ${filters.join(", ")}`);
  if (plan.group_by) parts.push(`grouped by ${DIMENSION_LABELS[plan.group_by].toLowerCase()}`);
  if (plan.sort) parts.push(plan.sort === "desc" ? "highest first" : "lowest first");
  if (plan.limit) parts.push(`top ${plan.limit}`);
  return parts.join(", ");
}

interface AskAnswerProps {
  response: AskResponse;
}

export function AskAnswer({ response }: AskAnswerProps) {
  if (response.status === "unsupported") {
    return (
      <div role="status" className="rounded border border-slate-200 bg-white p-4 text-sm">
        <p className="font-semibold">This question is not supported</p>
        <p className="mt-1 text-slate-700">{response.answer}</p>
      </div>
    );
  }

  const rows = response.result?.rows ?? [];
  const grouped = response.plan?.group_by ?? null;
  const currency = response.result?.currency ?? "USD";

  return (
    <div className="space-y-4">
      <div role="status" className="rounded border border-slate-200 bg-white p-4 text-sm">
        <p className="font-semibold">Answer</p>
        <p className="mt-1 text-slate-800">{response.answer}</p>
        {response.plan && (
          <p className="mt-2 text-xs text-slate-500">Interpreted as: {describePlan(response.plan)}</p>
        )}
      </div>
      {grouped && rows.length > 0 && (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">{DIMENSION_LABELS[grouped]}</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Employees</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">
                  Total payroll ({currency})
                </th>
                <th scope="col" className="px-3 py-2 text-right font-medium">
                  Average salary ({currency})
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key ?? ""} className="border-t border-slate-200">
                  <th scope="row" className="px-3 py-2 text-left font-normal">{row.key}</th>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {row.employee_count.toLocaleString("en-US")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatSalary(row.total_payroll_usd, currency)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {row.average_salary_usd === null ? "—" : formatSalary(row.average_salary_usd, currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
