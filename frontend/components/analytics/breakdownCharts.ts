import type { BarChartRow } from "@/components/analytics/BarChart";
import { analyticsHref } from "@/lib/api/analytics";
import { formatSalary } from "@/lib/formatting/money";
import type { AnalyticsBreakdown, AnalyticsFilters, GroupBy } from "@/types/analytics";

export type ChartMetric = "employee_count" | "total_payroll_usd" | "average_salary_usd";

/**
 * Maps an API breakdown onto chart rows. Magnitudes size the bars only; displayed values are the
 * API's exact decimal strings, and each row links to the same page filtered by that dimension.
 */
export function chartRows(
  breakdown: AnalyticsBreakdown,
  metric: ChartMetric,
  filters: AnalyticsFilters,
): BarChartRow[] {
  const dimension: GroupBy = breakdown.group_by;
  return breakdown.rows.map((row) => {
    const value = metric === "employee_count" ? String(row.employee_count) : row[metric];
    const magnitude = value === null ? 0 : Number(value);
    const display =
      metric === "employee_count"
        ? row.employee_count.toLocaleString("en-US")
        : value === null
          ? "—"
          : formatSalary(value, breakdown.currency);
    const detail =
      metric === "employee_count"
        ? undefined
        : `${row.employee_count.toLocaleString("en-US")} employees`;
    return {
      key: row.key,
      magnitude: Number.isFinite(magnitude) ? magnitude : 0,
      display,
      detail,
      href: analyticsHref({ ...filters, [dimension]: row.key }),
      selected: filters[dimension] === row.key,
    };
  });
}
