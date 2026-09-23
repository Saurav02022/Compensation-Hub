import type { Metadata } from "next";

import { RememberDirectory } from "@/components/employees/DirectoryMemory";
import { EmployeeTable } from "@/components/employees/EmployeeTable";
import { EmployeeToolbar } from "@/components/employees/EmployeeToolbar";
import { Pagination } from "@/components/employees/Pagination";
import { Frame, PageHeader } from "@/components/ui/Page";
import { PendingContent, RouteTransitionProvider } from "@/components/ui/RouteTransition";
import {
  employeesHref,
  fetchEmployees,
  fetchFilterOptions,
  hasActiveFilters,
  queryFromSearchParams,
} from "@/lib/api/employees";

export const metadata: Metadata = { title: "Employees" };

export default async function EmployeesPage(props: PageProps<"/employees">) {
  const query = queryFromSearchParams(await props.searchParams);
  const [page, filterOptions] = await Promise.all([fetchEmployees(query), fetchFilterOptions()]);
  const filtered = hasActiveFilters(query);
  const outOfRange = page.items.length === 0 && page.total_items > 0;

  return (
    <RouteTransitionProvider>
      <div className="space-y-5">
        <PageHeader title="Employees" description="Find a person to review or update their current salary." />
        <EmployeeToolbar query={query} options={filterOptions} />
        <Frame>
          <PendingContent>
            <EmployeeTable
              employees={page.items}
              filtered={filtered}
              outOfRange={outOfRange ? { firstPageHref: employeesHref({ ...query, page: 1 }) } : undefined}
            />
            {page.items.length > 0 && (
              <div className="border-t border-border">
                <Pagination
                  query={query}
                  page={page.page}
                  pageSize={page.page_size}
                  totalPages={page.total_pages}
                  totalItems={page.total_items}
                />
              </div>
            )}
          </PendingContent>
        </Frame>
      </div>
      <RememberDirectory href={employeesHref(query)} />
    </RouteTransitionProvider>
  );
}
