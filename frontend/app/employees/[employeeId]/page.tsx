import Link from "next/link";
import { notFound } from "next/navigation";

import { CompensationForm } from "@/components/compensation/CompensationForm";
import { EmployeeDetails } from "@/components/employees/EmployeeDetails";
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
    <div className="space-y-6">
      <Link href="/employees" className="text-sm text-slate-700 hover:underline">
        ← Back to employees
      </Link>
      <div>
        <h1 className="text-2xl font-semibold">{employee.full_name}</h1>
        <p className="text-sm text-slate-600">{employee.employee_code}</p>
      </div>
      <EmployeeDetails employee={employee} />
      <section aria-labelledby="compensation-heading" className="rounded border border-slate-200 bg-white p-4">
        <h2 id="compensation-heading" className="text-lg font-semibold">
          Update current compensation
        </h2>
        <CompensationForm action={action} compensation={employee.compensation} />
      </section>
    </div>
  );
}
