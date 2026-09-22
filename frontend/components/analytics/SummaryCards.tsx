import { StatTile } from "@/components/ui/Surface";
import { formatSalary } from "@/lib/formatting/money";
import type { AnalyticsSummary } from "@/types/analytics";

interface SummaryCardsProps {
  summary: AnalyticsSummary;
  scope?: string;
}

export function SummaryCards({ summary, scope = "Whole organization" }: SummaryCardsProps) {
  const currencyNote = `${summary.currency}, normalized with seeded exchange rates`;

  return (
    <dl className="grid gap-3 sm:grid-cols-3">
      <StatTile label="Employees" value={summary.employee_count.toLocaleString("en-US")} note={scope} />
      <StatTile
        label="Total annual payroll"
        value={formatSalary(summary.total_payroll_usd, summary.currency)}
        note={currencyNote}
      />
      <StatTile
        label="Average annual salary"
        value={summary.average_salary_usd === null ? "—" : formatSalary(summary.average_salary_usd, summary.currency)}
        note={summary.average_salary_usd === null ? "No salaries to average" : currencyNote}
      />
    </dl>
  );
}
