import type { GroupBy } from "./analytics";

export type AskMetric = "employee_count" | "average_salary" | "total_payroll";

export interface QueryPlan {
  metric: AskMetric;
  filters: {
    country: string | null;
    department: string | null;
    job_title: string | null;
  };
  group_by: GroupBy | null;
  sort: "asc" | "desc" | null;
  limit: number | null;
}

export interface AskResultRow {
  key: string | null;
  employee_count: number;
  total_payroll_usd: string;
  average_salary_usd: string | null;
}

export interface AskResponse {
  status: "answered" | "unsupported";
  question: string;
  answer: string;
  plan: QueryPlan | null;
  result: { currency: "USD"; rows: AskResultRow[] } | null;
}
