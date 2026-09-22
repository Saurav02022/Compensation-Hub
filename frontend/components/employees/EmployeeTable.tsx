import Link from "next/link";

import { buttonClassName } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";
import { formatSalary } from "@/lib/formatting/money";
import type { Employee } from "@/types/employees";

interface EmployeeTableProps {
  employees: Employee[];
  filtered: boolean;
}

const HEADER_CELL = "px-4 py-2.5 text-xs font-medium text-ink-secondary";

export function EmployeeTable({ employees, filtered }: EmployeeTableProps) {
  if (employees.length === 0) {
    return filtered ? (
      <EmptyState
        title="No employees match"
        description="Try a different name or code, or remove a filter."
        action={
          <Link href="/employees" className={buttonClassName("secondary")}>
            Clear search and filters
          </Link>
        }
      />
    ) : (
      <EmptyState title="No employees yet" description="Employees appear here once the dataset has been loaded." />
    );
  }

  return (
    <div className="overflow-x-auto rounded-surface border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead className="border-b border-border bg-surface-muted text-left">
          <tr>
            <th scope="col" className={HEADER_CELL}>Name</th>
            <th scope="col" className={HEADER_CELL}>Code</th>
            <th scope="col" className={HEADER_CELL}>Department</th>
            <th scope="col" className={HEADER_CELL}>Job title</th>
            <th scope="col" className={HEADER_CELL}>Country</th>
            <th scope="col" className={`${HEADER_CELL} text-right`}>Annual salary</th>
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => (
            <tr key={employee.id} className="border-b border-border last:border-b-0 hover:bg-surface-muted">
              <th scope="row" className="px-4 py-2.5 text-left font-normal">
                <Link href={`/employees/${employee.id}`} className="font-medium text-ink hover:text-accent hover:underline">
                  {employee.full_name}
                </Link>
              </th>
              <td className="px-4 py-2.5 font-mono text-xs text-ink-secondary">{employee.employee_code}</td>
              <td className="px-4 py-2.5 text-ink">{employee.department}</td>
              <td className="px-4 py-2.5 text-ink">{employee.job_title}</td>
              <td className="px-4 py-2.5 text-ink">{employee.country}</td>
              <td className="px-4 py-2.5 text-right tabular-nums text-ink">
                {employee.compensation
                  ? formatSalary(employee.compensation.annual_salary, employee.compensation.currency_code)
                  : <span className="text-ink-muted">Not on record</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
