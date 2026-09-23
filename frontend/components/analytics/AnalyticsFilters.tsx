"use client";

import { Button } from "@/components/ui/Button";
import { FilterSelect } from "@/components/ui/FilterSelect";
import { useRouteTransition } from "@/components/ui/RouteTransition";
import { analyticsHref, hasAnalyticsFilters, type AnalyticsView } from "@/lib/api/analytics";
import type { AnalyticsFilters as Filters } from "@/types/analytics";
import type { EmployeeFilterOptions } from "@/types/employees";

interface AnalyticsFiltersProps {
  filters: Filters;
  view: AnalyticsView;
  options: EmployeeFilterOptions;
}

const FILTERS: { key: keyof Filters; label: string; optionsKey: keyof EmployeeFilterOptions }[] = [
  { key: "country", label: "Country", optionsKey: "countries" },
  { key: "department", label: "Department", optionsKey: "departments" },
  { key: "job_title", label: "Job title", optionsKey: "job_titles" },
];

/** One row of filters that scope every figure on the page. */
export function AnalyticsFilters({ filters, view, options }: AnalyticsFiltersProps) {
  const { replace } = useRouteTransition();

  return (
    <div role="group" aria-label="Analytics filters" className="flex flex-wrap items-center gap-2">
      {FILTERS.map((filter) => (
        <FilterSelect
          key={filter.key}
          label={filter.label}
          value={filters[filter.key]}
          options={options[filter.optionsKey]}
          onChange={(value) => replace(analyticsHref({ ...filters, [filter.key]: value }, view))}
        />
      ))}
      {hasAnalyticsFilters(filters) && (
        <Button variant="ghost" size="sm" onClick={() => replace(analyticsHref({}, view))}>
          Clear all
        </Button>
      )}
    </div>
  );
}
