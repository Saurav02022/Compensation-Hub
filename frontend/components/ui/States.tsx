import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div role="status" className="rounded-surface border border-dashed border-border-strong bg-surface px-6 py-10 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {description && <p className="mt-1 text-sm text-ink-secondary">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

type AlertTone = "info" | "success" | "warning" | "error";

const ALERT_TONES: Record<AlertTone, string> = {
  info: "border-border bg-surface-muted text-ink-secondary",
  success: "border-positive-ink/20 bg-positive-soft text-positive-ink",
  warning: "border-warning-ink/20 bg-warning-soft text-warning-ink",
  error: "border-negative-ink/20 bg-negative-soft text-negative-ink",
};

const ALERT_PREFIX: Record<AlertTone, string> = {
  info: "Note",
  success: "Saved",
  warning: "Unavailable",
  error: "Error",
};

interface AlertProps {
  tone: AlertTone;
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}

export function Alert({ tone, title, children, action }: AlertProps) {
  const role = tone === "error" || tone === "warning" ? "alert" : "status";
  return (
    <div role={role} className={`flex flex-wrap items-start gap-3 rounded-surface border px-4 py-3 text-sm ${ALERT_TONES[tone]}`}>
      <div className="min-w-0 flex-1">
        <span className="font-semibold">{title ?? ALERT_PREFIX[tone]}.</span> {children}
      </div>
      {action}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-control bg-border ${className}`} />;
}

export function TableSkeleton({ rows = 8, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div role="status" aria-label="Loading" className="overflow-hidden rounded-surface border border-border bg-surface">
      <div className="border-b border-border bg-surface-muted px-4 py-3">
        <Skeleton className="h-3 w-40" />
      </div>
      {Array.from({ length: rows }).map((_, row) => (
        <div key={row} className="grid gap-4 border-b border-border px-4 py-3 last:border-b-0" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
          {Array.from({ length: columns }).map((_, column) => (
            <Skeleton key={column} className="h-3" />
          ))}
        </div>
      ))}
    </div>
  );
}
