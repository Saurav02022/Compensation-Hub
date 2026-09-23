import Link from "next/link";

import { Icon } from "@/components/ui/Icon";

export interface RankedItem {
  key: string;
  /** Numeric magnitude used only to size the bar; the displayed value comes from `display`. */
  magnitude: number;
  display: string;
  href: string;
}

interface RankedListProps {
  title: string;
  titleId: string;
  unit?: string;
  items: RankedItem[];
  footer: { href: string; label: string };
}

/** A compact top-N list with a bar per row, used where the full breakdown would be too much. */
export function RankedList({ title, titleId, unit, items, footer }: RankedListProps) {
  const max = items.reduce((current, item) => Math.max(current, item.magnitude), 0);
  return (
    <section aria-labelledby={titleId} className="flex flex-col rounded-surface border border-border bg-surface">
      <div className="flex h-11 items-center justify-between gap-3 border-b border-border px-4">
        <h2 id={titleId} className="text-sm font-semibold text-ink">
          {title}
        </h2>
        {unit && <span className="text-xs text-ink-muted">{unit}</span>}
      </div>
      <ol className="flex-1 py-1.5">
        {items.map((item) => (
          <li key={item.key}>
            <Link
              href={item.href}
              className="group grid grid-cols-[minmax(6.5rem,34%)_1fr_auto] items-center gap-3 px-4 py-2 text-[13px] hover:bg-surface-muted"
            >
              <span className="truncate text-ink group-hover:text-accent">{item.key}</span>
              <span aria-hidden="true" className="h-2.5">
                <span
                  className="block h-full rounded-r-[3px] bg-bar transition-colors group-hover:bg-accent"
                  style={{ width: `${max > 0 ? (item.magnitude / max) * 100 : 0}%` }}
                />
              </span>
              <span className="min-w-[5.5rem] text-right tabular-nums text-ink">{item.display}</span>
            </Link>
          </li>
        ))}
      </ol>
      <Link
        href={footer.href}
        className="flex h-10 items-center justify-between border-t border-border px-4 text-[13px] text-ink-secondary hover:bg-surface-muted hover:text-ink"
      >
        {footer.label}
        <Icon name="arrowRight" size={14} />
      </Link>
    </section>
  );
}
