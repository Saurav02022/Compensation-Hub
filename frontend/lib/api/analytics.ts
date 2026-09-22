import type {
  AnalyticsBreakdown,
  AnalyticsFilters,
  AnalyticsSummary,
  GroupBy,
} from "@/types/analytics";
import { apiFetch } from "./client";

export type RawSearchParams = Record<string, string | string[] | undefined>;

function firstValue(value: string | string[] | undefined): string | undefined {
  const single = Array.isArray(value) ? value[0] : value;
  const trimmed = single?.trim();
  return trimmed ? trimmed : undefined;
}

/** Reads the analytics filters from URL search params, ignoring blank values. */
export function filtersFromSearchParams(searchParams: RawSearchParams): AnalyticsFilters {
  return {
    country: firstValue(searchParams.country),
    department: firstValue(searchParams.department),
    job_title: firstValue(searchParams.job_title),
  };
}

export function analyticsSearchParams(filters: AnalyticsFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.country) params.set("country", filters.country);
  if (filters.department) params.set("department", filters.department);
  if (filters.job_title) params.set("job_title", filters.job_title);
  return params;
}

export function fetchSummary(filters: AnalyticsFilters): Promise<AnalyticsSummary> {
  const params = analyticsSearchParams(filters).toString();
  return apiFetch<AnalyticsSummary>(params ? `/analytics/summary?${params}` : "/analytics/summary");
}

export function fetchBreakdown(
  groupBy: GroupBy,
  filters: AnalyticsFilters,
): Promise<AnalyticsBreakdown> {
  const params = analyticsSearchParams(filters);
  params.set("group_by", groupBy);
  params.set("sort_by", "total_payroll_usd");
  params.set("descending", "true");
  return apiFetch<AnalyticsBreakdown>(`/analytics/breakdown?${params.toString()}`);
}
