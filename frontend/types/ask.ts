export type AskPlanKind = "aggregate" | "employees" | "values" | "share" | "compare";

export type AskMetric =
  | "employee_count"
  | "average_salary"
  | "total_payroll"
  | "minimum_salary"
  | "maximum_salary"
  | "median_salary";

export type AskDimension = "country" | "department" | "job_title" | "currency_code";

export interface QueryFilters {
  countries: string[];
  departments: string[];
  job_titles: string[];
  currency_codes: string[];
  employee_code: string | null;
  name_contains: string | null;
  salary_usd_min: string | number | null;
  salary_usd_max: string | number | null;
  has_compensation: boolean | null;
}

export interface QueryPlan {
  kind: AskPlanKind;
  metric: AskMetric | null;
  filters: QueryFilters;
  denominator_filters: QueryFilters | null;
  compare_filters: QueryFilters | null;
  group_by: AskDimension | null;
  field: AskDimension | null;
  sort: "asc" | "desc" | null;
  sort_by: "full_name" | "employee_code" | "salary_usd" | "annual_salary" | null;
  limit: number | null;
  target_currency: string | null;
  comparison: "difference" | "percent_difference" | "ratio" | null;
}

export interface AskHistoryItem {
  question: string;
  plan: QueryPlan;
}

export type AskResultFormat = "text" | "count" | "currency" | "percent";

export interface AskResultColumn {
  key: string;
  label: string;
  format: AskResultFormat;
}

export type AskResultCell = string | number | null;

export interface AskResult {
  kind: "scalar" | "table" | "employees";
  currency: string | null;
  columns: AskResultColumn[];
  rows: Record<string, AskResultCell>[];
}

export interface AskResponse {
  status: "answered" | "unsupported";
  question: string;
  answer: string;
  interpretation: string | null;
  plan: QueryPlan | null;
  result: AskResult | null;
  analytics_path: string | null;
}
