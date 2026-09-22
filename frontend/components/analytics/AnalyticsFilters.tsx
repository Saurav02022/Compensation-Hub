"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui/Button";
import { Field, Select } from "@/components/ui/Field";
import { analyticsHref, hasAnalyticsFilters } from "@/lib/api/analytics";
import type { AnalyticsFilters as Filters } from "@/types/analytics";
import type { EmployeeFilterOptions } from "@/types/employees";

interface AnalyticsFiltersProps {
  filters: Filters;
  options: EmployeeFilterOptions;
}

type FilterKey = keyof Filters;

const FILTERS: { key: FilterKey; label: string; optionsKey: keyof EmployeeFilterOptions }[] = [
  { key: "country", label: "Country", optionsKey: "countries" },
  { key: "department", label: "Department", optionsKey: "departments" },
  { key: "job_title", label: "Job title", optionsKey: "job_titles" },
];

export function AnalyticsFilters({ filters, options }: AnalyticsFiltersProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const active = hasAnalyticsFilters(filters);

  function apply(next: Filters) {
    startTransition(() => {
      router.replace(analyticsHref(next));
    });
  }

  return (
    <form
      aria-label="Analytics filters"
      onSubmit={(event) => event.preventDefault()}
      className="rounded-surface border border-border bg-surface px-4 py-3"
    >
      <div className="grid gap-3 sm:grid-cols-3">
        {FILTERS.map((filter) => (
          <Field key={filter.key} label={filter.label} htmlFor={`analytics-${filter.key}`}>
            <Select
              id={`analytics-${filter.key}`}
              value={filters[filter.key] ?? ""}
              onChange={(event) => apply({ ...filters, [filter.key]: event.target.value || undefined })}
            >
              <option value="">All</option>
              {options[filter.optionsKey].map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          </Field>
        ))}
      </div>
      <div className="mt-2 flex min-h-5 items-center justify-between gap-3 text-xs">
        <p role="status" aria-live="polite" className="text-ink-muted">
          {isPending ? "Updating analytics…" : active ? "Filters apply to every metric and chart on this page." : "Showing the whole organization."}
        </p>
        {active && (
          <Button variant="ghost" onClick={() => apply({})} className="h-7 px-2 text-xs">
            Clear all
          </Button>
        )}
      </div>
    </form>
  );
}
