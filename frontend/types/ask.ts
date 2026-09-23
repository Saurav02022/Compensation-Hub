export type AskDataField =
  | "employee_code"
  | "full_name"
  | "country"
  | "department"
  | "job_title"
  | "annual_salary"
  | "currency_code"
  | "salary_usd"
  | "rate_to_usd"
  | "has_compensation";

export type AskFilterOperator =
  | "eq"
  | "neq"
  | "in"
  | "not_in"
  | "contains"
  | "starts_with"
  | "ends_with"
  | "gt"
  | "gte"
  | "lt"
  | "lte"
  | "is_null"
  | "not_null";

export type AskAggregate =
  | "count"
  | "count_distinct"
  | "sum"
  | "avg"
  | "min"
  | "max"
  | "median"
  | "stddev"
  | "variance"
  | "percentile";

export interface AskFilterClause {
  field: AskDataField;
  op: AskFilterOperator;
  values: string[];
}

export interface AskProjection {
  alias: string;
  field?: AskDataField | null;
  aggregate?: AskAggregate | null;
  percentile?: string | number | null;
}

export interface AskOrderClause {
  key: string;
  direction: "asc" | "desc";
}

export interface AskDataQuery {
  name: string;
  select: AskProjection[];
  filters: AskFilterClause[];
  group_by: AskDataField[];
  order_by: AskOrderClause[];
  distinct: boolean;
  limit: number | null;
  target_currency: string | null;
}

export interface AskResultRef {
  query: string;
  column: string;
}

export interface AskCalculation {
  op: "add" | "subtract" | "multiply" | "divide" | "percentage" | "percent_difference" | "ratio";
  left: AskResultRef;
  right: AskResultRef;
  label: string;
  format: AskResultFormat;
}

export interface QueryProgram {
  queries: AskDataQuery[];
  calculation: AskCalculation | null;
}

export interface AskHistoryItem {
  question: string;
  plan: QueryProgram;
}

export type AskResultFormat = "text" | "number" | "count" | "currency" | "percent";

export interface AskResultColumn {
  key: string;
  label: string;
  format: AskResultFormat;
}

export type AskResultCell = string | number | null;

export interface AskResult {
  kind: "scalar" | "table";
  currency: string | null;
  columns: AskResultColumn[];
  rows: Record<string, AskResultCell>[];
}

export interface AskResponse {
  status: "answered" | "unsupported";
  question: string;
  answer: string;
  interpretation: string | null;
  plan: QueryProgram | null;
  result: AskResult | null;
  analytics_path: string | null;
}
