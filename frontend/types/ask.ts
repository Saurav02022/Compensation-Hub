import type { GroupBy } from "./analytics";

/**
 * An earlier answered question with the validated SQL and currency it used. The frontend never
 * interprets the SQL; it is only sent back so the planner can resolve follow-up questions, and the
 * backend validates it again. Result figures are never part of a turn.
 */
export interface AskTurn {
  question: string;
  sql: string;
  currency: string;
}

export type ResultColumnType = "text" | "count" | "money" | "percent" | "number";

export interface ResultColumn {
  key: string;
  label: string;
  type: ResultColumnType;
  /** Currency of every amount in a money column. */
  currency: string | null;
  /** For per-employee local salaries: the column holding each row's currency. */
  currency_key: string | null;
}

/** Exact decimals arrive as strings, counts as numbers, and missing values as null. */
export type ResultValue = string | number | null;

export interface ResultRow {
  values: ResultValue[];
  employee_id: number | null;
}

export interface AskResult {
  kind: "scalar" | "table";
  columns: ResultColumn[];
  rows: ResultRow[];
  /** The column holding the headline figure; null for plain employee lists. */
  primary: string | null;
  total_rows: number;
}

export interface AskAnalyticsView {
  group_by: GroupBy | null;
  metric: "headcount" | "payroll" | "average";
  country: string | null;
  department: string | null;
  job_title: string | null;
}

export interface AskResponse {
  status: "answered" | "missing_data" | "unsupported";
  question: string;
  answer: string;
  interpretation: string | null;
  missing: string[];
  sql: string | null;
  currency: string;
  result: AskResult | null;
  analytics_view: AskAnalyticsView | null;
}
