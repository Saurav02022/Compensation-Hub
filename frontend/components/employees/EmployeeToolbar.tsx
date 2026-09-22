"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { Button } from "@/components/ui/Button";
import { Field, Input, Select } from "@/components/ui/Field";
import { employeesHref, hasActiveFilters } from "@/lib/api/employees";
import type { EmployeeFilterOptions, EmployeeListQuery } from "@/types/employees";

const SEARCH_DEBOUNCE_MS = 300;

interface EmployeeToolbarProps {
  query: EmployeeListQuery;
  options: EmployeeFilterOptions;
}

type FilterKey = "country" | "department" | "job_title";

const FILTERS: { key: FilterKey; label: string; optionsKey: keyof EmployeeFilterOptions }[] = [
  { key: "country", label: "Country", optionsKey: "countries" },
  { key: "department", label: "Department", optionsKey: "departments" },
  { key: "job_title", label: "Job title", optionsKey: "job_titles" },
];

export function EmployeeToolbar({ query, options }: EmployeeToolbarProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [search, setSearch] = useState(query.search ?? "");
  const [syncedSearch, setSyncedSearch] = useState(query.search);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep the box in step with the URL when navigation (back, forward, a link) changes it.
  if (query.search !== syncedSearch) {
    setSyncedSearch(query.search);
    setSearch(query.search ?? "");
  }

  useEffect(
    () => () => {
      if (debounce.current) clearTimeout(debounce.current);
    },
    [],
  );

  function navigate(next: EmployeeListQuery) {
    startTransition(() => {
      router.replace(employeesHref({ ...next, page: 1 }));
    });
  }

  function onSearchChange(value: string) {
    setSearch(value);
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      const trimmed = value.trim();
      if (trimmed === (query.search ?? "")) return;
      navigate({ ...query, search: trimmed || undefined });
    }, SEARCH_DEBOUNCE_MS);
  }

  function onFilterChange(key: FilterKey, value: string) {
    navigate({ ...query, [key]: value || undefined });
  }

  function clearAll() {
    if (debounce.current) clearTimeout(debounce.current);
    setSearch("");
    navigate({});
  }

  const active = hasActiveFilters(query);

  return (
    <form
      role="search"
      aria-label="Employee search and filters"
      onSubmit={(event) => {
        event.preventDefault();
        if (debounce.current) clearTimeout(debounce.current);
        navigate({ ...query, search: search.trim() || undefined });
      }}
      className="rounded-surface border border-border bg-surface px-4 py-3"
    >
      <div className="grid gap-3 md:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
        <Field label="Search" htmlFor="employee-search">
          <div className="relative">
            <Input
              id="employee-search"
              type="search"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Name or employee code"
              maxLength={100}
              autoComplete="off"
              className={search ? "pr-16" : ""}
            />
            {search && (
              <button
                type="button"
                onClick={() => onSearchChange("")}
                className="absolute inset-y-0 right-2 text-xs text-ink-secondary hover:text-ink"
              >
                Clear
              </button>
            )}
          </div>
        </Field>
        {FILTERS.map((filter) => (
          <Field key={filter.key} label={filter.label} htmlFor={`filter-${filter.key}`}>
            <Select
              id={`filter-${filter.key}`}
              value={query[filter.key] ?? ""}
              onChange={(event) => onFilterChange(filter.key, event.target.value)}
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
          {isPending ? "Updating results…" : active ? "Filters applied. Results update as you type." : "Results update as you type."}
        </p>
        {active && (
          <Button variant="ghost" onClick={clearAll} className="h-7 px-2 text-xs">
            Clear all
          </Button>
        )}
      </div>
    </form>
  );
}
