import type { ReactNode } from "react";

export interface MetricItem {
  label: string;
  value: string;
  unit?: string;
  /** Exact value offered on hover when the displayed value is rounded. */
  exact?: string;
  note?: ReactNode;
}

/** A single strip of headline figures separated by hairlines, rather than a row of cards. */
export function MetricStrip({ items, label }: { items: MetricItem[]; label: string }) {
  return (
    <dl aria-label={label} className="grid overflow-hidden rounded-surface border border-border bg-surface sm:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="border-b border-border px-5 py-4 last:border-b-0 sm:border-r sm:border-b-0 sm:last:border-r-0">
          <dt className="text-[13px] text-ink-secondary">{item.label}</dt>
          <dd className="mt-1.5 flex items-baseline gap-1.5" title={item.exact}>
            {item.unit && <span className="text-sm font-medium text-ink-muted">{item.unit}</span>}
            <span className="text-[26px] leading-8 font-semibold tracking-[-0.02em] text-ink">{item.value}</span>
          </dd>
          {item.note && <dd className="mt-1 text-xs text-ink-muted">{item.note}</dd>}
        </div>
      ))}
    </dl>
  );
}
