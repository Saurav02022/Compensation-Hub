import { AnalyticsFilters } from "@/components/analytics/AnalyticsFilters";
import { BreakdownTable } from "@/components/analytics/BreakdownTable";
import { SummaryCards } from "@/components/analytics/SummaryCards";
import { fetchBreakdown, fetchSummary, filtersFromSearchParams } from "@/lib/api/analytics";
import { fetchFilterOptions } from "@/lib/api/employees";

export default async function AnalyticsPage(props: PageProps<"/analytics">) {
  const filters = filtersFromSearchParams(await props.searchParams);
  const [summary, byCountry, byDepartment, byJobTitle, filterOptions] = await Promise.all([
    fetchSummary(filters),
    fetchBreakdown("country", filters),
    fetchBreakdown("department", filters),
    fetchBreakdown("job_title", filters),
    fetchFilterOptions(),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Compensation overview</h1>
        <p className="text-sm text-slate-600">
          Organization-wide metrics are shown in {summary.currency}. Salaries stored in other
          currencies are converted with the seeded exchange rates.
        </p>
      </div>
      <AnalyticsFilters filters={filters} options={filterOptions} />
      <SummaryCards summary={summary} />
      <BreakdownTable breakdown={byCountry} />
      <BreakdownTable breakdown={byDepartment} />
      <BreakdownTable breakdown={byJobTitle} />
    </div>
  );
}
