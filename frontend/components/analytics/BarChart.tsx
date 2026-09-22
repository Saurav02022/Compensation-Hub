import Link from "next/link";

import { Surface } from "@/components/ui/Surface";

export interface BarChartRow {
  key: string;
  /** Numeric magnitude used only to size the bar; the displayed value comes from `display`. */
  magnitude: number;
  display: string;
  detail?: string;
  href?: string;
  selected?: boolean;
}

interface BarChartProps {
  title: string;
  description?: string;
  rows: BarChartRow[];
  dimensionLabel: string;
  valueLabel: string;
  initialCount?: number;
  emptyMessage?: string;
}

function Bar({ row, max, dimensionLabel, valueLabel }: { row: BarChartRow; max: number; dimensionLabel: string; valueLabel: string }) {
  const width = max > 0 ? Math.max((row.magnitude / max) * 100, row.magnitude > 0 ? 1 : 0) : 0;
  const tooltip = `${row.key}: ${row.display}${row.detail ? ` (${row.detail})` : ""}`;
  const label = row.href ? (
    <Link href={row.href} className="truncate text-ink hover:text-accent hover:underline" title={`Filter analytics by ${dimensionLabel.toLowerCase()} ${row.key}`}>
      {row.key}
    </Link>
  ) : (
    <span className="truncate text-ink">{row.key}</span>
  );

  return (
    <li className={`grid grid-cols-[minmax(7rem,30%)_1fr_auto] items-center gap-3 rounded-control px-2 py-1 text-sm hover:bg-surface-muted ${row.selected ? "bg-accent-soft" : ""}`} title={tooltip}>
      <span className="flex min-w-0 items-center gap-2">
        {label}
        {row.selected && (
          <span className="shrink-0 rounded-full border border-accent px-1.5 text-[10px] font-medium uppercase tracking-wide text-accent-ink">
            Selected
          </span>
        )}
      </span>
      <span className="h-5 w-full">
        <span
          aria-hidden="true"
          className={`block h-full rounded-r ${row.selected ? "bg-accent-hover" : "bg-accent"}`}
          style={{ width: `${width}%` }}
        />
      </span>
      <span className="text-right text-sm tabular-nums text-ink">
        <span className="sr-only">{valueLabel}: </span>
        {row.display}
      </span>
    </li>
  );
}

export function BarChart({ title, description, rows, dimensionLabel, valueLabel, initialCount = 10, emptyMessage = "No employees match the current filters." }: BarChartProps) {
  const max = rows.reduce((current, row) => Math.max(current, row.magnitude), 0);
  const visible = rows.slice(0, initialCount);
  const rest = rows.slice(initialCount);

  return (
    <Surface>
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {description && <p className="mt-0.5 text-xs text-ink-muted">{description}</p>}
      </div>
      <figure className="px-2 py-3">
        <figcaption className="sr-only">
          {title}: {valueLabel} by {dimensionLabel.toLowerCase()}
        </figcaption>
        {rows.length === 0 ? (
          <p role="status" className="px-2 py-6 text-center text-sm text-ink-secondary">
            {emptyMessage}
          </p>
        ) : (
          <>
            <ol className="space-y-0.5">
              {visible.map((row) => (
                <Bar key={row.key} row={row} max={max} dimensionLabel={dimensionLabel} valueLabel={valueLabel} />
              ))}
            </ol>
            {rest.length > 0 && (
              <details className="mt-1 px-2">
                <summary className="cursor-pointer text-xs font-medium text-ink-secondary hover:text-ink">
                  Show all {rows.length}
                </summary>
                <ol className="mt-1 space-y-0.5">
                  {rest.map((row) => (
                    <Bar key={row.key} row={row} max={max} dimensionLabel={dimensionLabel} valueLabel={valueLabel} />
                  ))}
                </ol>
              </details>
            )}
          </>
        )}
      </figure>
    </Surface>
  );
}
