import Link from "next/link";

import type { EmployeeFilterOptions, EmployeeListQuery } from "@/types/employees";

interface EmployeeFiltersProps {
  query: EmployeeListQuery;
  options: EmployeeFilterOptions;
}

interface SelectFilterProps {
  name: string;
  label: string;
  value: string | undefined;
  options: string[];
}

function SelectFilter({ name, label, value, options }: SelectFilterProps) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium">{label}</span>
      <select
        name={name}
        defaultValue={value ?? ""}
        className="rounded border border-slate-300 bg-white px-2 py-1.5"
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function EmployeeFilters({ query, options }: EmployeeFiltersProps) {
  const hasActiveFilters = Boolean(
    query.search || query.country || query.department || query.job_title,
  );

  return (
    <form
      method="get"
      action="/employees"
      aria-label="Employee filters"
      className="grid gap-3 rounded border border-slate-200 bg-white p-4 md:grid-cols-5"
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Search</span>
        <input
          type="search"
          name="search"
          defaultValue={query.search ?? ""}
          placeholder="Name or employee code"
          maxLength={100}
          className="rounded border border-slate-300 px-2 py-1.5"
        />
      </label>
      <SelectFilter name="country" label="Country" value={query.country} options={options.countries} />
      <SelectFilter
        name="department"
        label="Department"
        value={query.department}
        options={options.departments}
      />
      <SelectFilter
        name="job_title"
        label="Job title"
        value={query.job_title}
        options={options.job_titles}
      />
      <div className="flex items-end gap-3">
        <button
          type="submit"
          className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
        >
          Apply
        </button>
        {hasActiveFilters && (
          <Link href="/employees" className="text-sm text-slate-700 hover:underline">
            Clear
          </Link>
        )}
      </div>
    </form>
  );
}
