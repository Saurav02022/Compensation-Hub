import Link from "next/link";

import { buttonClassName } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";
import { formatAmount } from "@/lib/formatting/money";
import type { Employee } from "@/types/employees";

interface EmployeeTableProps {
  employees: Employee[];
  filtered: boolean;
  /** Set when the requested page is past the end of a non-empty result set. */
  outOfRange?: { firstPageHref: string };
}

const HEAD = "h-9 px-4 text-left text-xs font-medium whitespace-nowrap text-ink-muted";

/*
 * Columns collapse by the width of the table's container rather than the viewport, so the table
 * stays readable when the Ask Compensation panel is docked beside it.
 *   wide   (>= 56rem): Name | Code | Job title | Department | Country | Annual salary
 *   medium (>= 42rem): Employee (name, code) | Role (title, department) | Country | Annual salary
 *   narrow           : Employee (name, code, title, country) | Annual salary
 */
export function EmployeeTable({ employees, filtered, outOfRange }: EmployeeTableProps) {
  if (employees.length === 0) {
    if (outOfRange) {
      return (
        <EmptyState
          title="This page is past the end of the results"
          description="The list is shorter than the page in the address. Go back to the first page."
          action={
            <Link href={outOfRange.firstPageHref} className={buttonClassName("secondary")}>
              First page
            </Link>
          }
        />
      );
    }
    return filtered ? (
      <EmptyState
        title="No employees match"
        description="Check the spelling of the name or code, or remove a filter."
        action={
          <Link href="/employees" className={buttonClassName("secondary")}>
            Clear search and filters
          </Link>
        }
      />
    ) : (
      <EmptyState
        icon="employees"
        title="No employees yet"
        description="Employees appear here once the dataset has been loaded."
      />
    );
  }

  return (
    <div className="@container">
      <table className="w-full text-[13px]">
        <caption className="sr-only">Employees</caption>
        <thead className="sticky top-12 z-10 bg-surface-muted shadow-[inset_0_-1px_0_var(--color-border)] lg:top-0">
          <tr>
            <th scope="col" className={HEAD}>
              <span className="@2xl:hidden">Employee</span>
              <span className="hidden @2xl:inline">Name</span>
            </th>
            <th scope="col" className={`${HEAD} hidden @4xl:table-cell`}>
              Code
            </th>
            <th scope="col" className={`${HEAD} hidden @2xl:table-cell`}>
              <span className="@4xl:hidden">Role</span>
              <span className="hidden @4xl:inline">Job title</span>
            </th>
            <th scope="col" className={`${HEAD} hidden @4xl:table-cell`}>
              Department
            </th>
            <th scope="col" className={`${HEAD} hidden @2xl:table-cell`}>
              Country
            </th>
            <th scope="col" className={`${HEAD} text-right`}>
              Annual salary
            </th>
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => (
            <tr
              key={employee.id}
              className="relative border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted has-[a:focus-visible]:bg-accent-soft/60"
            >
              <th scope="row" className="px-4 py-2.5 text-left align-top font-normal @4xl:py-0 @4xl:align-middle">
                <span className="flex h-full min-h-5 items-center">
                  <Link
                    href={`/employees/${employee.id}`}
                    className="font-medium text-ink after:absolute after:inset-0 after:content-[''] hover:text-accent focus-visible:underline focus-visible:outline-none"
                  >
                    {employee.full_name}
                  </Link>
                  <span className="ml-2 font-mono text-[11px] text-ink-muted @4xl:hidden">{employee.employee_code}</span>
                </span>
                <span className="mt-0.5 block text-xs text-ink-muted @2xl:hidden">
                  {employee.job_title} · {employee.country}
                </span>
              </th>
              <td className="hidden h-10 px-4 font-mono text-xs whitespace-nowrap text-ink-secondary @4xl:table-cell">
                {employee.employee_code}
              </td>
              <td className="hidden px-4 py-2.5 align-top text-ink @2xl:table-cell @4xl:py-0 @4xl:align-middle">
                {employee.job_title}
                <span className="mt-0.5 block text-xs text-ink-muted @4xl:hidden">{employee.department}</span>
              </td>
              <td className="hidden px-4 text-ink @4xl:table-cell">{employee.department}</td>
              <td className="hidden px-4 py-2.5 align-top whitespace-nowrap text-ink @2xl:table-cell @4xl:py-0 @4xl:align-middle">
                {employee.country}
              </td>
              <td className="px-4 py-2.5 text-right align-top whitespace-nowrap @4xl:py-0 @4xl:align-middle">
                {employee.compensation ? (
                  <>
                    <span className="tabular-nums text-ink">
                      {formatAmount(employee.compensation.annual_salary, employee.compensation.currency_code)}
                    </span>
                    <span className="ml-1.5 inline-block w-7 text-left text-[11px] font-medium text-ink-muted">
                      {employee.compensation.currency_code}
                    </span>
                  </>
                ) : (
                  <span className="text-ink-muted">Not on record</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
