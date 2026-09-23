"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Kbd } from "@/components/ui/Field";
import { FilterSelect } from "@/components/ui/FilterSelect";
import { Icon } from "@/components/ui/Icon";
import { useRouteTransition } from "@/components/ui/RouteTransition";
import { employeesHref, hasActiveFilters } from "@/lib/api/employees";
import type { EmployeeFilterOptions, EmployeeListQuery } from "@/types/employees";

const SEARCH_DEBOUNCE_MS = 300;

type FilterKey = "country" | "department" | "job_title";

const FILTERS: { key: FilterKey; label: string; optionsKey: keyof EmployeeFilterOptions }[] = [
  { key: "country", label: "Country", optionsKey: "countries" },
  { key: "department", label: "Department", optionsKey: "departments" },
  { key: "job_title", label: "Job title", optionsKey: "job_titles" },
];

interface EmployeeToolbarProps {
  query: EmployeeListQuery;
  options: EmployeeFilterOptions;
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

export function EmployeeToolbar({ query, options }: EmployeeToolbarProps) {
  const { replace } = useRouteTransition();
  const [search, setSearch] = useState(query.search ?? "");
  const [syncedSearch, setSyncedSearch] = useState(query.search);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Keep the box in step with the URL when navigation (back, forward, a link) changes it.
  if (query.search !== syncedSearch) {
    setSyncedSearch(query.search);
    setSearch(query.search ?? "");
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey || isTypingTarget(event.target)) return;
      event.preventDefault();
      searchRef.current?.focus();
      searchRef.current?.select();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (debounce.current) clearTimeout(debounce.current);
    };
  }, []);

  function navigate(next: EmployeeListQuery) {
    replace(employeesHref({ ...next, page: 1 }));
  }

  function commitSearch(value: string) {
    if (debounce.current) clearTimeout(debounce.current);
    const trimmed = value.trim();
    if (trimmed === (query.search ?? "")) return;
    navigate({ ...query, search: trimmed || undefined });
  }

  function onSearchChange(value: string) {
    setSearch(value);
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => commitSearch(value), SEARCH_DEBOUNCE_MS);
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
        commitSearch(search);
      }}
      className="flex flex-wrap items-center gap-2"
    >
      <div className="relative w-full sm:w-72">
        <label htmlFor="employee-search" className="sr-only">
          Search
        </label>
        <Icon name="search" className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ink-muted" />
        <input
          id="employee-search"
          ref={searchRef}
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape" && search) {
              event.preventDefault();
              onSearchChange("");
            }
          }}
          placeholder="Search name or employee code"
          maxLength={100}
          autoComplete="off"
          spellCheck={false}
          className="h-8 w-full rounded-control border border-border-strong bg-surface pr-8 pl-8 text-[13px] text-ink shadow-[0_1px_0_rgb(17_24_39/0.03)] transition-colors placeholder:text-ink-muted hover:border-ink-muted/60 focus:border-accent focus:ring-3 focus:ring-accent/15 focus:outline-none focus-visible:outline-none [&::-webkit-search-cancel-button]:hidden"
        />
        {search ? (
          <button
            type="button"
            onClick={() => {
              onSearchChange("");
              searchRef.current?.focus();
            }}
            aria-label="Clear search"
            className="absolute top-1/2 right-1.5 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded text-ink-muted hover:bg-surface-hover hover:text-ink"
          >
            <Icon name="close" size={14} />
          </button>
        ) : (
          <Kbd className="pointer-events-none absolute top-1/2 right-2 hidden -translate-y-1/2 sm:inline-flex">/</Kbd>
        )}
      </div>
      {FILTERS.map((filter) => (
        <FilterSelect
          key={filter.key}
          label={filter.label}
          value={query[filter.key]}
          options={options[filter.optionsKey]}
          onChange={(value) => navigate({ ...query, [filter.key]: value })}
        />
      ))}
      {active && (
        <Button variant="ghost" size="sm" onClick={clearAll}>
          Clear all
        </Button>
      )}
    </form>
  );
}
