import { EmployeeFilters } from "@/components/employees/EmployeeFilters";
import { EmployeeTable } from "@/components/employees/EmployeeTable";
import { Pagination } from "@/components/employees/Pagination";
import { fetchEmployees, fetchFilterOptions, queryFromSearchParams } from "@/lib/api/employees";

export default async function EmployeesPage(props: PageProps<"/employees">) {
  const query = queryFromSearchParams(await props.searchParams);
  const [page, filterOptions] = await Promise.all([fetchEmployees(query), fetchFilterOptions()]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Employees</h1>
        <p className="text-sm text-slate-600">
          Search by name or employee code, and filter by country, department, or job title.
        </p>
      </div>
      <EmployeeFilters query={query} options={filterOptions} />
      <EmployeeTable employees={page.items} />
      <Pagination query={query} page={page.page} totalPages={page.total_pages} totalItems={page.total_items} />
    </div>
  );
}
