import Link from "next/link";

import { employeeListSearchParams } from "@/lib/api/employees";
import type { EmployeeListQuery } from "@/types/employees";

interface PaginationProps {
  query: EmployeeListQuery;
  page: number;
  totalPages: number;
  totalItems: number;
}

function pageHref(query: EmployeeListQuery, page: number): string {
  const params = employeeListSearchParams({ ...query, page }).toString();
  return params ? `/employees?${params}` : "/employees";
}

export function Pagination({ query, page, totalPages, totalItems }: PaginationProps) {
  const linkClass = "rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100";
  const disabledClass = "rounded border border-slate-200 px-3 py-1.5 text-sm text-slate-400";

  return (
    <nav aria-label="Pagination" className="flex items-center justify-between">
      <p className="text-sm text-slate-600">
        {totalItems === 1 ? "1 employee" : `${totalItems.toLocaleString("en-US")} employees`}
      </p>
      <div className="flex items-center gap-3">
        {page > 1 ? (
          <Link href={pageHref(query, page - 1)} className={linkClass}>
            Previous
          </Link>
        ) : (
          <span aria-disabled="true" className={disabledClass}>
            Previous
          </span>
        )}
        <span className="text-sm">
          Page {page} of {totalPages}
        </span>
        {page < totalPages ? (
          <Link href={pageHref(query, page + 1)} className={linkClass}>
            Next
          </Link>
        ) : (
          <span aria-disabled="true" className={disabledClass}>
            Next
          </span>
        )}
      </div>
    </nav>
  );
}
