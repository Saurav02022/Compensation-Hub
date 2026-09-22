import Link from "next/link";
import { notFound } from "next/navigation";

import { CompensationPanel } from "@/components/compensation/CompensationPanel";
import { EmployeeDetails } from "@/components/employees/EmployeeDetails";
import { PageHeader } from "@/components/ui/Surface";
import { ApiError } from "@/lib/api/client";
import { fetchEmployee } from "@/lib/api/employees";
import type { Employee } from "@/types/employees";
import { updateCompensationAction } from "./actions";

async function loadEmployee(rawId: string): Promise<Employee> {
  const employeeId = Number.parseInt(rawId, 10);
  if (!Number.isInteger(employeeId) || employeeId <= 0 || String(employeeId) !== rawId) {
    notFound();
  }
  try {
    return await fetchEmployee(employeeId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}

export default async function EmployeePage(props: PageProps<"/employees/[employeeId]">) {
  const { employeeId } = await props.params;
  const employee = await loadEmployee(employeeId);
  const action = updateCompensationAction.bind(null, employee.id);

  return (
    <div className="space-y-4">
      <nav aria-label="Breadcrumb" className="text-sm">
        <Link href="/employees" className="text-ink-secondary hover:text-ink hover:underline">
          Employees
        </Link>
        <span aria-hidden="true" className="mx-2 text-ink-muted">
          /
        </span>
        <span className="text-ink">{employee.full_name}</span>
      </nav>
      <PageHeader
        title={employee.full_name}
        description={`${employee.job_title} · ${employee.department} · ${employee.country}`}
        meta={<span className="font-mono">{employee.employee_code}</span>}
      />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <EmployeeDetails employee={employee} />
        <CompensationPanel action={action} compensation={employee.compensation} />
      </div>
    </div>
  );
}
