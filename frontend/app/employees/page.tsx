import { EmployeeTable } from "@/components/employees/EmployeeTable";
import { EmployeeToolbar } from "@/components/employees/EmployeeToolbar";
import { Pagination } from "@/components/employees/Pagination";
import { PageHeader } from "@/components/ui/Surface";
import {
  fetchEmployees,
  fetchFilterOptions,
  hasActiveFilters,
  queryFromSearchParams,
} from "@/lib/api/employees";

export default async function EmployeesPage(props: PageProps<"/employees">) {
  const query = queryFromSearchParams(await props.searchParams);
  const [page, filterOptions] = await Promise.all([fetchEmployees(query), fetchFilterOptions()]);
  const filtered = hasActiveFilters(query);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Employees"
        description="Find an employee and open their current compensation."
        meta={`${page.total_items.toLocaleString("en-US")} ${page.total_items === 1 ? "employee" : "employees"}${filtered ? " match" : ""}`}
      />
      <EmployeeToolbar query={query} options={filterOptions} />
      <EmployeeTable employees={page.items} filtered={filtered} />
      {page.total_items > 0 && (
        <Pagination
          query={query}
          page={page.page}
          pageSize={page.page_size}
          totalPages={page.total_pages}
          totalItems={page.total_items}
        />
      )}
    </div>
  );
}
