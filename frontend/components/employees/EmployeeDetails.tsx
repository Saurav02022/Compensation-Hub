import { Surface } from "@/components/ui/Surface";
import type { Employee } from "@/types/employees";

interface EmployeeDetailsProps {
  employee: Employee;
}

const ROWS: { label: string; key: "employee_code" | "country" | "department" | "job_title" }[] = [
  { label: "Employee code", key: "employee_code" },
  { label: "Country", key: "country" },
  { label: "Department", key: "department" },
  { label: "Job title", key: "job_title" },
];

export function EmployeeDetails({ employee }: EmployeeDetailsProps) {
  return (
    <Surface>
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Profile</h2>
      </div>
      <dl className="divide-y divide-border">
        {ROWS.map((row) => (
          <div key={row.key} className="grid grid-cols-[9rem_1fr] gap-3 px-4 py-2.5 text-sm">
            <dt className="text-ink-secondary">{row.label}</dt>
            <dd className={row.key === "employee_code" ? "font-mono text-ink" : "text-ink"}>{employee[row.key]}</dd>
          </div>
        ))}
      </dl>
    </Surface>
  );
}
