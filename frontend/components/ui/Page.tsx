import type { ReactNode } from "react";

interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({ title, description, actions, children }: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="min-w-0">
        <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-ink">{title}</h1>
        {description && <p className="mt-1 text-[13px] text-ink-secondary">{description}</p>}
        {children}
      </div>
      {actions && <div className="flex w-full items-center gap-2 sm:w-auto sm:shrink-0">{actions}</div>}
    </header>
  );
}

interface SectionProps {
  title: string;
  titleId?: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Section({ title, titleId, description, actions, children, className = "" }: SectionProps) {
  return (
    <section aria-labelledby={titleId} className={className}>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 id={titleId} className="text-sm font-semibold text-ink">
            {title}
          </h2>
          {description && <p className="mt-0.5 text-[13px] text-ink-muted">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

/** The bordered frame for tables and lists; content supplies its own internal dividers. */
export function Frame({ children, className = "" }: { children: ReactNode; className?: string }) {
  // `overflow: clip` rounds the corners without creating a scroll container, so sticky table headers still stick to the page.
  return <div className={`overflow-clip rounded-surface border border-border bg-surface ${className}`}>{children}</div>;
}
