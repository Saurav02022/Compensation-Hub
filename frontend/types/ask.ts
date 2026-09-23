export type AskDataField =
  | "employee_code"
  | "full_name"
  | "country"
  | "department"
  | "job_title"
  | "annual_salary"
  | "currency_code"
  | "salary_usd"
  | "rate_to_usd";

export type PredicateOperator =
  | "equals"
  | "not_equals"
  | "in"
  | "contains"
  | "greater_than"
  | "greater_than_or_equal"
  | "less_than"
  | "less_than_or_equal"
  | "is_null"
  | "is_not_null";

export interface QueryPredicate {
  field: AskDataField;
  operator: PredicateOperator;
  value?: string | number | boolean | null;
  values?: (string | number | boolean)[];
}

export type QueryExpression =
  | { kind: "field"; field: AskDataField }
  | {
      kind: "aggregate";
      function: "count" | "sum" | "average" | "minimum" | "maximum" | "median";
      field?: AskDataField | null;
      distinct?: boolean;
      where?: QueryPredicate[];
    }
  | { kind: "literal"; value: number | string }
  | {
      kind: "binary";
      operator: "add" | "subtract" | "multiply" | "divide";
      left: QueryExpression;
      right: QueryExpression;
    }
  | {
      kind: "currency";
      currency_code: string;
      expression: QueryExpression;
    };

export type AskResultFormat = "text" | "number" | "count" | "currency" | "percent";

export interface QuerySelectItem {
  alias: string;
  label: string;
  expression: QueryExpression;
  format: AskResultFormat;
}

export interface QueryPlan {
  select: QuerySelectItem[];
  where: QueryPredicate[];
  group_by: AskDataField[];
  distinct: boolean;
  order_by: { key: string; direction: "asc" | "desc" }[];
  limit: number;
}

export interface AskHistoryItem {
  question: string;
  plan: QueryPlan;
}

export interface AskResultColumn {
  key: string;
  label: string;
  format: AskResultFormat;
}

export type AskResultCell = string | number | null;

export interface AskResult {
  kind: "scalar" | "table";
  currency_by_column: Record<string, string>;
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
}
