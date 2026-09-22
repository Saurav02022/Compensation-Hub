import Link from "next/link";

import { formatSalary } from "@/lib/formatting/money";
import type { Employee } from "@/types/employees";

interface EmployeeTableProps {
  employees: Employee[];
}

export function EmployeeTable({ employees }: EmployeeTableProps) {
  if (employees.length === 0) {
    return (
      <p role="status" className="rounded border border-slate-200 bg-white p-6 text-center text-sm text-slate-600">
        No employees match the current search and filters.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded border border-slate-200 bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100 text-left">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">Employee code</th>
            <th scope="col" className="px-3 py-2 font-medium">Name</th>
            <th scope="col" className="px-3 py-2 font-medium">Country</th>
            <th scope="col" className="px-3 py-2 font-medium">Department</th>
            <th scope="col" className="px-3 py-2 font-medium">Job title</th>
            <th scope="col" className="px-3 py-2 text-right font-medium">Annual salary</th>
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => (
            <tr key={employee.id} className="border-t border-slate-200">
              <td className="px-3 py-2">
                <Link href={`/employees/${employee.id}`} className="font-mono text-slate-900 hover:underline">
                  {employee.employee_code}
                </Link>
              </td>
              <td className="px-3 py-2">
                <Link href={`/employees/${employee.id}`} className="hover:underline">
                  {employee.full_name}
                </Link>
              </td>
              <td className="px-3 py-2">{employee.country}</td>
              <td className="px-3 py-2">{employee.department}</td>
              <td className="px-3 py-2">{employee.job_title}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {employee.compensation
                  ? formatSalary(employee.compensation.annual_salary, employee.compensation.currency_code)
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
