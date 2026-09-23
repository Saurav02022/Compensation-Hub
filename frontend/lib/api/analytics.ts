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

export type AnalyticsMetric = "payroll" | "average" | "headcount";

export interface AnalyticsView {
  by: GroupBy;
  metric: AnalyticsMetric;
}

export const DEFAULT_VIEW: AnalyticsView = { by: "country", metric: "payroll" };

const GROUP_BY_VALUES: readonly GroupBy[] = ["country", "department", "job_title"];
const METRIC_VALUES: readonly AnalyticsMetric[] = ["payroll", "average", "headcount"];

/** The breakdown sort key that ranks rows by the chosen metric. */
export const METRIC_SORT: Record<AnalyticsMetric, BreakdownSort> = {
  payroll: "total_payroll_usd",
  average: "average_salary_usd",
  headcount: "employee_count",
};

/** Reads which breakdown the analytics page shows, falling back to the default for unknown values. */
export function viewFromSearchParams(searchParams: RawSearchParams): AnalyticsView {
  const by = firstValue(searchParams.by);
  const metric = firstValue(searchParams.metric);
  return {
    by: GROUP_BY_VALUES.find((value) => value === by) ?? DEFAULT_VIEW.by,
    metric: METRIC_VALUES.find((value) => value === metric) ?? DEFAULT_VIEW.metric,
  };
}

/** Analytics URL for filters and a breakdown view; defaults are omitted so URLs stay clean. */
export function analyticsHref(filters: AnalyticsFilters, view: Partial<AnalyticsView> = {}): string {
  const params = analyticsSearchParams(filters);
  if (view.by && view.by !== DEFAULT_VIEW.by) params.set("by", view.by);
  if (view.metric && view.metric !== DEFAULT_VIEW.metric) params.set("metric", view.metric);
  const query = params.toString();
  return query ? `/analytics?${query}` : "/analytics";
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
