import { formatSalary } from "@/lib/formatting/money";
import type { Employee } from "@/types/employees";

interface EmployeeDetailsProps {
  employee: Employee;
}

export function EmployeeDetails({ employee }: EmployeeDetailsProps) {
  const salary = employee.compensation
    ? formatSalary(employee.compensation.annual_salary, employee.compensation.currency_code)
    : "No compensation on record";

  return (
    <dl className="grid gap-4 rounded border border-slate-200 bg-white p-4 text-sm md:grid-cols-2">
      <div>
        <dt className="text-slate-600">Country</dt>
        <dd className="font-medium">{employee.country}</dd>
      </div>
      <div>
        <dt className="text-slate-600">Department</dt>
        <dd className="font-medium">{employee.department}</dd>
      </div>
      <div>
        <dt className="text-slate-600">Job title</dt>
        <dd className="font-medium">{employee.job_title}</dd>
      </div>
      <div>
        <dt className="text-slate-600">Current annual salary</dt>
        <dd className="font-medium tabular-nums">{salary}</dd>
      </div>
    </dl>
  );
}
