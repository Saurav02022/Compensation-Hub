import type { ReactNode } from "react";

import { Icon, type IconName } from "./Icon";

interface EmptyStateProps {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: IconName;
  role?: "status" | "alert";
  className?: string;
}

export function EmptyState({ title, description, action, icon = "search", role = "status", className = "" }: EmptyStateProps) {
  return (
    <div role={role} className={`flex flex-col items-center px-6 py-14 text-center ${className}`}>
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-hover text-ink-muted">
        <Icon name={icon} />
      </span>
      <p className="mt-3 text-sm font-medium text-ink">{title}</p>
      {description && <p className="mt-1 max-w-sm text-[13px] text-ink-secondary">{description}</p>}
      {action && <div className="mt-4 flex justify-center gap-2">{action}</div>}
    </div>
  );
}

type AlertTone = "info" | "success" | "warning" | "error";

const ALERT_TONES: Record<AlertTone, string> = {
  info: "border-border bg-surface-muted text-ink-secondary",
  success: "border-positive-ink/15 bg-positive-soft text-positive-ink",
  warning: "border-warning-ink/15 bg-warning-soft text-warning-ink",
  error: "border-negative-ink/15 bg-negative-soft text-negative-ink",
};

const ALERT_ICONS: Record<AlertTone, IconName> = {
  info: "info",
  success: "check",
  warning: "alert",
  error: "alert",
};

interface AlertProps {
  tone: AlertTone;
  title?: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function Alert({ tone, title, children, action, className = "" }: AlertProps) {
  const role = tone === "error" || tone === "warning" ? "alert" : "status";
  return (
    <div role={role} className={`flex items-start gap-2.5 rounded-control border px-3 py-2.5 text-[13px] ${ALERT_TONES[tone]} ${className}`}>
      <Icon name={ALERT_ICONS[tone]} className="mt-px" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={title ? "mt-0.5 opacity-90" : ""}>{children}</div>}
      </div>
      {action && <div className="-my-0.5 shrink-0">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded bg-surface-hover ${className}`} />;
}

/** A thin indeterminate bar shown while the visible data is being refreshed in place. */
export function RefreshBar({ active }: { active: boolean }) {
  return (
    <div aria-hidden="true" className="relative h-0.5 overflow-hidden">
      {active && <div className="absolute inset-y-0 left-0 w-2/5 animate-progress rounded-full bg-accent/70" />}
    </div>
  );
}

export function TableSkeleton({ rows = 10, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div aria-hidden="true">
      <div className="flex h-9 items-center gap-6 border-b border-border px-4">
        {Array.from({ length: columns }).map((_, column) => (
          <Skeleton key={column} className="h-2.5 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, row) => (
        <div key={row} className="flex h-10 items-center gap-6 border-b border-border px-4 last:border-b-0">
          {Array.from({ length: columns }).map((_, column) => (
            <Skeleton key={column} className={`h-2.5 flex-1 ${column === 0 ? "max-w-40" : ""}`} />
          ))}
        </div>
      ))}
    </div>
  );
}
