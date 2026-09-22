import { formatSalary } from "@/lib/formatting/money";
import type { AnalyticsSummary } from "@/types/analytics";

interface SummaryCardsProps {
  summary: AnalyticsSummary;
}

interface CardProps {
  label: string;
  value: string;
  note?: string;
}

function Card({ label, value, note }: CardProps) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tabular-nums">{value}</dd>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </div>
  );
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  const currencyNote = `Normalized to ${summary.currency} with seeded exchange rates`;

  return (
    <dl className="grid gap-4 md:grid-cols-3">
      <Card label="Employees" value={summary.employee_count.toLocaleString("en-US")} />
      <Card
        label="Total annual payroll"
        value={formatSalary(summary.total_payroll_usd, summary.currency)}
        note={currencyNote}
      />
      <Card
        label="Average annual salary"
        value={
          summary.average_salary_usd === null
            ? "—"
            : formatSalary(summary.average_salary_usd, summary.currency)
        }
        note={summary.average_salary_usd === null ? "No salaries to average" : currencyNote}
      />
    </dl>
  );
}
