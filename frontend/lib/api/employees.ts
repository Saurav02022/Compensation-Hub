import type {
  Compensation,
  CompensationUpdate,
  Employee,
  EmployeeFilterOptions,
  EmployeeListQuery,
  EmployeePage,
} from "@/types/employees";
import { apiFetch } from "./client";

export type RawSearchParams = Record<string, string | string[] | undefined>;

function firstValue(value: string | string[] | undefined): string | undefined {
  const single = Array.isArray(value) ? value[0] : value;
  const trimmed = single?.trim();
  return trimmed ? trimmed : undefined;
}

function pageNumber(value: string | string[] | undefined): number {
  const parsed = Number.parseInt(firstValue(value) ?? "", 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

/** Reads the directory query from URL search params, ignoring blank or malformed values. */
export function queryFromSearchParams(searchParams: RawSearchParams): EmployeeListQuery {
  return {
    page: pageNumber(searchParams.page),
    search: firstValue(searchParams.search),
    country: firstValue(searchParams.country),
    department: firstValue(searchParams.department),
    job_title: firstValue(searchParams.job_title),
  };
}

export function employeeListSearchParams(query: EmployeeListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.page && query.page > 1) params.set("page", String(query.page));
  if (query.page_size) params.set("page_size", String(query.page_size));
  if (query.search) params.set("search", query.search);
  if (query.country) params.set("country", query.country);
  if (query.department) params.set("department", query.department);
  if (query.job_title) params.set("job_title", query.job_title);
  return params;
}

export function fetchEmployees(query: EmployeeListQuery): Promise<EmployeePage> {
  const params = employeeListSearchParams(query).toString();
  return apiFetch<EmployeePage>(params ? `/employees?${params}` : "/employees");
}

export function fetchFilterOptions(): Promise<EmployeeFilterOptions> {
  return apiFetch<EmployeeFilterOptions>("/employees/filter-options");
}

export function fetchEmployee(employeeId: number): Promise<Employee> {
  return apiFetch<Employee>(`/employees/${employeeId}`);
}

export function updateCompensation(
  employeeId: number,
  payload: CompensationUpdate,
): Promise<Compensation> {
  return apiFetch<Compensation>(`/employees/${employeeId}/compensation`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
