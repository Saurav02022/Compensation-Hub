"use client";

import { buttonClassName } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { TransitionLink } from "@/components/ui/RouteTransition";
import { employeesHref } from "@/lib/api/employees";
import { formatCount } from "@/lib/formatting/money";
import type { EmployeeListQuery } from "@/types/employees";

interface PaginationProps {
  query: EmployeeListQuery;
  page: number;
  pageSize: number;
  totalPages: number;
  totalItems: number;
}

const STEP = buttonClassName("secondary", "w-8 px-0", "md");

export function Pagination({ query, page, pageSize, totalPages, totalItems }: PaginationProps) {
  const first = Math.min((page - 1) * pageSize + 1, totalItems);
  const last = Math.min(page * pageSize, totalItems);

  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
      <p className="text-[13px] text-ink-secondary">
        <span className="tabular-nums text-ink">
          {formatCount(first)}–{formatCount(last)}
        </span>{" "}
        of <span className="tabular-nums text-ink">{formatCount(totalItems)}</span>
      </p>
      <div className="flex items-center gap-2">
        <span className="text-[13px] tabular-nums text-ink-muted">
          Page {formatCount(page)} of {formatCount(totalPages)}
        </span>
        {page > 1 ? (
          <TransitionLink href={employeesHref({ ...query, page: page - 1 })} className={STEP} rel="prev" aria-label="Previous page">
            <Icon name="chevronLeft" />
          </TransitionLink>
        ) : (
          <span aria-disabled="true" aria-label="Previous page" role="link" className={STEP}>
            <Icon name="chevronLeft" />
          </span>
        )}
        {page < totalPages ? (
          <TransitionLink href={employeesHref({ ...query, page: page + 1 })} className={STEP} rel="next" aria-label="Next page">
            <Icon name="chevronRight" />
          </TransitionLink>
        ) : (
          <span aria-disabled="true" aria-label="Next page" role="link" className={STEP}>
            <Icon name="chevronRight" />
          </span>
        )}
      </div>
    </nav>
  );
}
