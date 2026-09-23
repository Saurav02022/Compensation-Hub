import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cache, type ReactNode } from "react";

import { CompensationPanel } from "@/components/compensation/CompensationPanel";
import { BackToDirectory } from "@/components/employees/DirectoryMemory";
import { Icon } from "@/components/ui/Icon";
import { ApiError } from "@/lib/api/client";
import { analyticsHref } from "@/lib/api/analytics";
import { fetchEmployee } from "@/lib/api/employees";
import type { Employee } from "@/types/employees";
import { updateCompensationAction } from "./actions";

const loadEmployee = cache(async (rawId: string): Promise<Employee> => {
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
});

export async function generateMetadata(props: PageProps<"/employees/[employeeId]">): Promise<Metadata> {
  const { employeeId } = await props.params;
  const employee = await loadEmployee(employeeId);
  return { title: employee.full_name };
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="mt-0.5 truncate text-[13px] text-ink">{children}</dd>
    </div>
  );
}

function ContextLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <li>
      <Link
        href={href}
        className="group flex items-center justify-between gap-3 px-3 py-2.5 text-[13px] text-ink hover:bg-surface-muted"
      >
        <span className="min-w-0">{children}</span>
        <Icon name="arrowRight" size={14} className="text-ink-muted transition-transform group-hover:translate-x-0.5" />
      </Link>
    </li>
  );
}

export default async function EmployeePage(props: PageProps<"/employees/[employeeId]">) {
  const { employeeId } = await props.params;
  const employee = await loadEmployee(employeeId);
  const action = updateCompensationAction.bind(null, employee.id);

  return (
    <div className="space-y-6">
      <nav aria-label="Breadcrumb">
        <BackToDirectory />
      </nav>

      <header>
        <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-ink">{employee.full_name}</h1>
        <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-3 border-y border-border py-3 sm:flex sm:flex-wrap">
          <Fact label="Employee code">
            <span className="font-mono text-xs">{employee.employee_code}</span>
          </Fact>
          <Fact label="Department">{employee.department}</Fact>
          <Fact label="Job title">{employee.job_title}</Fact>
          <Fact label="Country">{employee.country}</Fact>
        </dl>
      </header>

      <div className="@container">
        <div className="grid gap-6 @3xl:grid-cols-[minmax(0,1fr)_16rem]">
          <CompensationPanel action={action} compensation={employee.compensation} />
          <aside aria-labelledby="context-heading">
            <h2 id="context-heading" className="text-xs font-medium text-ink-muted">
              Compare in analytics
            </h2>
            <ul className="mt-2 divide-y divide-border overflow-hidden rounded-surface border border-border">
              <ContextLink
                href={analyticsHref(
                  { country: employee.country, job_title: employee.job_title },
                  { by: "job_title", metric: "average" },
                )}
              >
                {employee.job_title} in {employee.country}
              </ContextLink>
              <ContextLink href={analyticsHref({ department: employee.department }, { by: "job_title", metric: "average" })}>
                {employee.department} by job title
              </ContextLink>
              <ContextLink href={analyticsHref({ country: employee.country }, { by: "department", metric: "average" })}>
                {employee.country} by department
              </ContextLink>
            </ul>
            <p className="mt-2 text-xs text-ink-muted">Averages in USD at fixed exchange rates.</p>
          </aside>
        </div>
      </div>
    </div>
  );
}
