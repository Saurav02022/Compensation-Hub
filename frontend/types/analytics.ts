export type GroupBy = "country" | "department" | "job_title";

export interface AnalyticsFilters {
  country?: string;
  department?: string;
  job_title?: string;
}

export interface AnalyticsSummary {
  currency: "USD";
  employee_count: number;
  /** Exact decimal amounts serialized by the API as strings. */
  total_payroll_usd: string;
  average_salary_usd: string | null;
}

export interface BreakdownRow {
  key: string;
  employee_count: number;
  total_payroll_usd: string;
  average_salary_usd: string | null;
}

export interface AnalyticsBreakdown {
  group_by: GroupBy;
  currency: "USD";
  rows: BreakdownRow[];
}
