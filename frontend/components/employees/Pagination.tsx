import Link from "next/link";

import { buttonClassName } from "@/components/ui/Button";
import { employeesHref } from "@/lib/api/employees";
import type { EmployeeListQuery } from "@/types/employees";

interface PaginationProps {
  query: EmployeeListQuery;
  page: number;
  pageSize: number;
  totalPages: number;
  totalItems: number;
}

export function Pagination({ query, page, pageSize, totalPages, totalItems }: PaginationProps) {
  const first = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, totalItems);
  const format = (value: number) => value.toLocaleString("en-US");
  const disabled = buttonClassName("secondary", "pointer-events-none opacity-50");

  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-ink-secondary">
        {totalItems === 0
          ? "No results"
          : `Showing ${format(first)}–${format(last)} of ${format(totalItems)}`}
      </p>
      <div className="flex items-center gap-2">
        {page > 1 ? (
          <Link href={employeesHref({ ...query, page: page - 1 })} className={buttonClassName("secondary")} rel="prev">
            Previous
          </Link>
        ) : (
          <span aria-disabled="true" className={disabled}>
            Previous
          </span>
        )}
        <span className="px-1 text-sm tabular-nums text-ink-secondary">
          Page {format(page)} of {format(totalPages)}
        </span>
        {page < totalPages ? (
          <Link href={employeesHref({ ...query, page: page + 1 })} className={buttonClassName("secondary")} rel="next">
            Next
          </Link>
        ) : (
          <span aria-disabled="true" className={disabled}>
            Next
          </span>
        )}
      </div>
    </nav>
  );
}
