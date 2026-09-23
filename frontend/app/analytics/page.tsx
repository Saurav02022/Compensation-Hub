import type { Metadata } from "next";
import Link from "next/link";

import { AnalyticsFilters } from "@/components/analytics/AnalyticsFilters";
import { BreakdownExplorer } from "@/components/analytics/BreakdownExplorer";
import { SummaryMetrics, describeScope } from "@/components/analytics/SummaryMetrics";
import { buttonClassName } from "@/components/ui/Button";
import { Frame, PageHeader } from "@/components/ui/Page";
import { PendingContent, RouteTransitionProvider } from "@/components/ui/RouteTransition";
import { EmptyState } from "@/components/ui/States";
import {
  METRIC_SORT,
  analyticsHref,
  fetchBreakdown,
  fetchSummary,
  filtersFromSearchParams,
  viewFromSearchParams,
} from "@/lib/api/analytics";
import { fetchFilterOptions } from "@/lib/api/employees";

export const metadata: Metadata = { title: "Analytics" };

export default async function AnalyticsPage(props: PageProps<"/analytics">) {
  const searchParams = await props.searchParams;
  const filters = filtersFromSearchParams(searchParams);
  const view = viewFromSearchParams(searchParams);
  const [summary, breakdown, filterOptions] = await Promise.all([
    fetchSummary(filters),
    fetchBreakdown(view.by, filters, { sortBy: METRIC_SORT[view.metric] }),
    fetchFilterOptions(),
  ]);

  return (
    <RouteTransitionProvider>
      <div className="space-y-5">
        <PageHeader
          title="Analytics"
          description={`Organization-wide compensation in ${summary.currency}, converted from local salaries at fixed exchange rates.`}
        />
        <AnalyticsFilters filters={filters} view={view} options={filterOptions} />
        <PendingContent className="space-y-5">
          <SummaryMetrics summary={summary} scope={describeScope(filters)} />
          {summary.employee_count === 0 ? (
            <Frame>
              <EmptyState
                title="No employees match these filters"
                description="This combination of country, department, and job title has no employees. Remove a filter to widen it."
                action={
                  <Link href={analyticsHref({}, view)} className={buttonClassName("secondary")}>
                    Clear filters
                  </Link>
                }
              />
            </Frame>
          ) : (
            <BreakdownExplorer breakdown={breakdown} filters={filters} view={view} />
          )}
        </PendingContent>
      </div>
    </RouteTransitionProvider>
  );
}
