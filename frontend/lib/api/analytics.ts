import type {
  AnalyticsBreakdown,
  AnalyticsFilters,
  AnalyticsSummary,
  GroupBy,
} from "@/types/analytics";
import { apiFetch } from "./client";

export type RawSearchParams = Record<string, string | string[] | undefined>;

export type BreakdownSort = "key" | "employee_count" | "total_payroll_usd" | "average_salary_usd";

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

export function analyticsHref(filters: AnalyticsFilters): string {
  const params = analyticsSearchParams(filters).toString();
  return params ? `/analytics?${params}` : "/analytics";
}

export function hasAnalyticsFilters(filters: AnalyticsFilters): boolean {
  return Boolean(filters.country || filters.department || filters.job_title);
}

export function fetchSummary(filters: AnalyticsFilters): Promise<AnalyticsSummary> {
  const params = analyticsSearchParams(filters).toString();
  return apiFetch<AnalyticsSummary>(params ? `/analytics/summary?${params}` : "/analytics/summary");
}

export interface BreakdownOptions {
  sortBy?: BreakdownSort;
  limit?: number;
}

export function fetchBreakdown(
  groupBy: GroupBy,
  filters: AnalyticsFilters,
  options: BreakdownOptions = {},
): Promise<AnalyticsBreakdown> {
  const params = analyticsSearchParams(filters);
  params.set("group_by", groupBy);
  params.set("sort_by", options.sortBy ?? "total_payroll_usd");
  params.set("descending", "true");
  if (options.limit) params.set("limit", String(options.limit));
  return apiFetch<AnalyticsBreakdown>(`/analytics/breakdown?${params.toString()}`);
}
