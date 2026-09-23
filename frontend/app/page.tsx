import { RankedList, type RankedItem } from "@/components/analytics/RankedList";
import { SummaryMetrics } from "@/components/analytics/SummaryMetrics";
import { AskExamples } from "@/components/ask-compensation/AskExamples";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/Page";
import { analyticsHref, fetchBreakdown, fetchSummary } from "@/lib/api/analytics";
import { fetchFilterOptions } from "@/lib/api/employees";
import { formatAmount, formatCount } from "@/lib/formatting/money";
import type { AnalyticsBreakdown } from "@/types/analytics";

const EXAMPLE_QUESTIONS = [
  "What is the average salary in Engineering?",
  "What is the total payroll in Germany?",
  "How many Engineering employees are based in India?",
];

function payrollItems(breakdown: AnalyticsBreakdown): RankedItem[] {
  return breakdown.rows.map((row) => ({
    key: row.key,
    magnitude: Number(row.total_payroll_usd) || 0,
    display: formatAmount(row.total_payroll_usd, breakdown.currency, { whole: true }),
    href: analyticsHref({ country: row.key }, { by: "department", metric: "payroll" }),
  }));
}

function headcountItems(breakdown: AnalyticsBreakdown): RankedItem[] {
  return breakdown.rows.map((row) => ({
    key: row.key,
    magnitude: row.employee_count,
    display: formatCount(row.employee_count),
    href: analyticsHref({ department: row.key }, { by: "job_title", metric: "headcount" }),
  }));
}

export default async function OverviewPage() {
  const [summary, byCountry, byDepartment, options] = await Promise.all([
    fetchSummary({}),
    fetchBreakdown("country", {}, { sortBy: "total_payroll_usd", limit: 5 }),
    fetchBreakdown("department", {}, { sortBy: "employee_count", limit: 5 }),
    fetchFilterOptions(),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        description={`${formatCount(summary.employee_count)} employees across ${options.countries.length} countries and ${options.departments.length} departments.`}
        actions={
          <form action="/employees" role="search" aria-label="Find an employee" className="relative w-full sm:w-72">
            <label htmlFor="overview-search" className="sr-only">
              Find an employee
            </label>
            <Icon name="search" className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ink-muted" />
            <input
              id="overview-search"
              name="search"
              type="search"
              required
              maxLength={100}
              autoComplete="off"
              spellCheck={false}
              placeholder="Find an employee by name or code"
              className="h-8 w-full rounded-control border border-border-strong bg-surface pr-3 pl-8 text-[13px] text-ink shadow-[0_1px_0_rgb(17_24_39/0.03)] placeholder:text-ink-muted hover:border-ink-muted/60 focus:border-accent focus:ring-3 focus:ring-accent/15 focus:outline-none focus-visible:outline-none"
            />
          </form>
        }
      />

      <SummaryMetrics summary={summary} scope="Whole organization" />

      <div className="@container">
        <div className="grid gap-5 @2xl:grid-cols-2">
          <RankedList
            title="Largest payrolls by country"
            titleId="overview-payroll"
            unit={`Annual · ${byCountry.currency}`}
            items={payrollItems(byCountry)}
            footer={{ href: analyticsHref({}, { by: "country", metric: "payroll" }), label: "All countries in Analytics" }}
          />
          <RankedList
            title="Largest departments"
            titleId="overview-headcount"
            unit="Employees"
            items={headcountItems(byDepartment)}
            footer={{ href: analyticsHref({}, { by: "department", metric: "headcount" }), label: "All departments in Analytics" }}
          />
        </div>
      </div>

      <section aria-labelledby="overview-ask" className="border-t border-border pt-5">
        <h2 id="overview-ask" className="text-sm font-semibold text-ink">
          Ask a question
        </h2>
        <p className="mt-0.5 mb-3 text-[13px] text-ink-muted">
          Ask Compensation answers from the same figures as Analytics, in plain language.
        </p>
        <AskExamples questions={EXAMPLE_QUESTIONS} />
      </section>
    </div>
  );
}
