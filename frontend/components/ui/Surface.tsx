import type { HTMLAttributes, ReactNode } from "react";

export function Surface({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-surface border border-border bg-surface ${className}`}
      {...props}
    />
  );
}

interface PageHeaderProps {
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ title, description, meta, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-ink-secondary">{description}</p>}
        {meta && <div className="mt-1 text-sm text-ink-muted">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

interface SectionHeadingProps {
  id?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function SectionHeading({ id, title, description, actions }: SectionHeadingProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 id={id} className="text-base font-semibold text-ink">
          {title}
        </h2>
        {description && <p className="mt-0.5 text-xs text-ink-muted">{description}</p>}
      </div>
      {actions}
    </div>
  );
}

interface StatTileProps {
  label: string;
  value: string;
  note?: string;
}

export function StatTile({ label, value, note }: StatTileProps) {
  return (
    <Surface className="px-4 py-3">
      <dt className="text-xs font-medium text-ink-secondary">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tracking-tight text-ink tabular-nums">{value}</dd>
      {note && <p className="mt-1 text-xs text-ink-muted">{note}</p>}
    </Surface>
  );
}
