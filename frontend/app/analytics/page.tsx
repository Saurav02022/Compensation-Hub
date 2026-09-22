import { AnalyticsFilters } from "@/components/analytics/AnalyticsFilters";
import { BarChart } from "@/components/analytics/BarChart";
import { BreakdownTable } from "@/components/analytics/BreakdownTable";
import { SummaryCards } from "@/components/analytics/SummaryCards";
import { chartRows } from "@/components/analytics/breakdownCharts";
import { PageHeader } from "@/components/ui/Surface";
import { fetchBreakdown, fetchSummary, filtersFromSearchParams, hasAnalyticsFilters } from "@/lib/api/analytics";
import { fetchFilterOptions } from "@/lib/api/employees";
import type { AnalyticsFilters as Filters } from "@/types/analytics";

function describeScope(filters: Filters): string {
  const parts = [filters.country, filters.department, filters.job_title].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "Whole organization";
}

export default async function AnalyticsPage(props: PageProps<"/analytics">) {
  const filters = filtersFromSearchParams(await props.searchParams);
  const [summary, byCountry, byDepartment, byJobTitle, filterOptions] = await Promise.all([
    fetchSummary(filters),
    fetchBreakdown("country", filters, { sortBy: "total_payroll_usd" }),
    fetchBreakdown("department", filters, { sortBy: "average_salary_usd" }),
    fetchBreakdown("job_title", filters, { sortBy: "employee_count" }),
    fetchFilterOptions(),
  ]);
  const filtered = hasAnalyticsFilters(filters);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Analytics"
        description={`Organization-wide amounts are shown in ${summary.currency}, converted from local salaries with seeded exchange rates.`}
      />
      <AnalyticsFilters filters={filters} options={filterOptions} />
      <SummaryCards summary={summary} scope={describeScope(filters)} />

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <BarChart
            title="Total payroll by country"
            description={`Annual payroll in ${summary.currency}. Select a country to focus the page on it.`}
            rows={chartRows(byCountry, "total_payroll_usd", filters)}
            dimensionLabel="Country"
            valueLabel="Total payroll"
          />
          <details className="rounded-surface border border-border bg-surface">
            <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium text-ink-secondary hover:text-ink">
              Exact values by country
            </summary>
            <BreakdownTable breakdown={byCountry} caption="Exact values by country" />
          </details>
        </div>
        <div className="space-y-4">
          <BarChart
            title="Average salary by department"
            description={`Average annual salary in ${summary.currency}. Select a department to focus the page on it.`}
            rows={chartRows(byDepartment, "average_salary_usd", filters)}
            dimensionLabel="Department"
            valueLabel="Average salary"
          />
          <details className="rounded-surface border border-border bg-surface">
            <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium text-ink-secondary hover:text-ink">
              Exact values by department
            </summary>
            <BreakdownTable breakdown={byDepartment} caption="Exact values by department" />
          </details>
        </div>
      </div>

      <div className="space-y-4">
        <BarChart
          title="Headcount by job title"
          description={filtered ? "Employees matching the current filters, largest roles first." : "Largest roles first; expand to see every title."}
          rows={chartRows(byJobTitle, "employee_count", filters)}
          dimensionLabel="Job title"
          valueLabel="Employees"
          initialCount={10}
        />
        <details className="rounded-surface border border-border bg-surface">
          <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium text-ink-secondary hover:text-ink">
            Exact values by job title
          </summary>
          <BreakdownTable breakdown={byJobTitle} caption="Exact values by job title" />
        </details>
      </div>
    </div>
  );
}
