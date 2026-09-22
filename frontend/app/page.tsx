import Link from "next/link";

import { BarChart } from "@/components/analytics/BarChart";
import { SummaryCards } from "@/components/analytics/SummaryCards";
import { chartRows } from "@/components/analytics/breakdownCharts";
import { AskLauncherButton } from "@/components/ask-compensation/AskLauncherButton";
import { buttonClassName } from "@/components/ui/Button";
import { PageHeader, Surface } from "@/components/ui/Surface";
import { fetchBreakdown, fetchSummary } from "@/lib/api/analytics";

export default async function OverviewPage() {
  const [summary, byCountry, byDepartment] = await Promise.all([
    fetchSummary({}),
    fetchBreakdown("country", {}, { sortBy: "total_payroll_usd", limit: 5 }),
    fetchBreakdown("department", {}, { sortBy: "employee_count", limit: 5 }),
  ]);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Overview"
        description="Where the organization's current compensation stands, and where to go next."
        actions={
          <>
            <Link href="/employees" className={buttonClassName("secondary")}>
              Find an employee
            </Link>
            <Link href="/analytics" className={buttonClassName("primary")}>
              Open analytics
            </Link>
          </>
        }
      />
      <SummaryCards summary={summary} />

      <div className="grid gap-4 lg:grid-cols-2">
        <BarChart
          title="Largest payrolls by country"
          description={`Top five by total annual payroll in ${summary.currency}. Select a country to open it in analytics.`}
          rows={chartRows(byCountry, "total_payroll_usd", {})}
          dimensionLabel="Country"
          valueLabel="Total payroll"
        />
        <BarChart
          title="Largest departments"
          description="Top five by headcount. Select a department to open it in analytics."
          rows={chartRows(byDepartment, "employee_count", {})}
          dimensionLabel="Department"
          valueLabel="Employees"
        />
      </div>

      <Surface className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-ink">Have a question about pay?</h2>
          <p className="mt-0.5 text-xs text-ink-secondary">
            Ask in plain language, for example &ldquo;What is the average salary in Engineering?&rdquo; Answers use the
            same analytics as this page.
          </p>
        </div>
        <AskLauncherButton />
      </Surface>
    </div>
  );
}
