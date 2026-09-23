"use client";

import { useId } from "react";

import { Icon } from "./Icon";

interface FilterSelectProps {
  label: string;
  value: string | undefined;
  options: string[];
  onChange: (value: string | undefined) => void;
  allLabel?: string;
}

/**
 * A compact filter control that reads "Country · India". It is a native select underneath, so
 * keyboard use, type-ahead, and mobile pickers behave as the platform expects.
 */
export function FilterSelect({ label, value, options, onChange, allLabel = "All" }: FilterSelectProps) {
  const id = useId();
  const active = Boolean(value);

  return (
    <div
      className={`group relative inline-flex h-8 max-w-full items-center rounded-control border text-[13px] transition-colors has-[select:focus-visible]:outline-2 has-[select:focus-visible]:outline-offset-2 has-[select:focus-visible]:outline-accent ${
        active
          ? "border-accent/35 bg-accent-soft text-accent-ink"
          : "border-border-strong bg-surface text-ink hover:border-ink-muted/60 hover:bg-surface-muted"
      }`}
    >
      <span className="relative flex h-full min-w-0 items-center pl-2.5 pr-7">
        <label htmlFor={id} className={active ? "text-accent-ink/75" : "text-ink-muted"}>
          {label}
        </label>
        <span aria-hidden="true" className="ml-1.5 truncate font-medium md:max-w-44">
          {value ?? allLabel}
        </span>
        <Icon name="chevronDown" size={14} className="pointer-events-none absolute right-2 opacity-70" />
        <select
          id={id}
          value={value ?? ""}
          onChange={(event) => onChange(event.target.value || undefined)}
          className="absolute inset-0 w-full cursor-pointer appearance-none opacity-0"
        >
          <option value="">{allLabel}</option>
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </span>
      {active && (
        <button
          type="button"
          onClick={() => onChange(undefined)}
          aria-label={`Remove ${label.toLowerCase()} filter`}
          className="mr-1 -ml-1 flex h-6 w-6 items-center justify-center rounded text-accent-ink/70 hover:bg-accent/10 hover:text-accent-ink"
        >
          <Icon name="close" size={13} />
        </button>
      )}
    </div>
  );
}
