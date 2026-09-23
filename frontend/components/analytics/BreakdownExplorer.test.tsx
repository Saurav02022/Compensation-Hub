import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RouteTransitionProvider } from "@/components/ui/RouteTransition";
import type { AnalyticsView } from "@/lib/api/analytics";
import { resetRouter, router } from "@/test/router";
import type { AnalyticsBreakdown, AnalyticsFilters } from "@/types/analytics";
import { BreakdownExplorer } from "./BreakdownExplorer";

vi.mock("next/navigation", async () => {
  const { router: mockRouter } = await import("@/test/router");
  return { useRouter: () => mockRouter };
});

const byCountry: AnalyticsBreakdown = {
  group_by: "country",
  currency: "USD",
  rows: [
    { key: "United States", employee_count: 2570, total_payroll_usd: "306210500.00", average_salary_usd: "119147.28" },
    { key: "India", employee_count: 1967, total_payroll_usd: "70658280.40", average_salary_usd: "35921.85" },
  ],
};

function renderExplorer(breakdown: AnalyticsBreakdown, filters: AnalyticsFilters, view: AnalyticsView) {
  return render(
    <RouteTransitionProvider>
      <BreakdownExplorer breakdown={breakdown} filters={filters} view={view} />
    </RouteTransitionProvider>,
  );
}

describe("BreakdownExplorer", () => {
  beforeEach(resetRouter);

  it("titles the view and shows every measure beside the bars, rounded with exact values on hover", () => {
    renderExplorer(byCountry, {}, { by: "country", metric: "payroll" });

    expect(screen.getByRole("heading", { name: "Total payroll by country" })).toBeInTheDocument();
    const india = screen.getByRole("row", { name: /India/ });
    expect(within(india).getByText("1,967")).toBeInTheDocument();
    expect(within(india).getAllByText("70,658,280")[0]).toHaveAttribute("title", "70658280.40 USD");
    expect(within(india).getAllByText("35,922")[0]).toBeInTheDocument();
  });

  it("drills into a row by filtering to it and breaking down by the next open dimension", () => {
    renderExplorer(byCountry, { department: "Engineering" }, { by: "country", metric: "average" });

    const link = screen.getByRole("link", { name: "India" });
    expect(link).toHaveAttribute("href", "/analytics?country=India&department=Engineering&by=job_title&metric=average");

    fireEvent.click(link);
    expect(router.push).toHaveBeenCalledWith("/analytics?country=India&department=Engineering&by=job_title&metric=average");
  });

  it("switches dimension and measure through links that keep the filters", () => {
    renderExplorer(byCountry, { country: "India" }, { by: "department", metric: "payroll" });

    const dimensions = screen.getByRole("navigation", { name: "Break down by" });
    expect(within(dimensions).getByRole("link", { name: "Department" })).toHaveAttribute("aria-current", "true");
    expect(within(dimensions).getByRole("link", { name: "Job title" })).toHaveAttribute("href", "/analytics?country=India&by=job_title");

    const measures = screen.getByRole("navigation", { name: "Measure" });
    expect(within(measures).getByRole("link", { name: "Headcount" })).toHaveAttribute(
      "href",
      "/analytics?country=India&by=department&metric=headcount",
    );
  });

  it("shows the top rows first and reveals the rest on request", () => {
    const many: AnalyticsBreakdown = {
      group_by: "job_title",
      currency: "USD",
      rows: Array.from({ length: 15 }, (_, index) => ({
        key: `Role ${index + 1}`,
        employee_count: 100 - index,
        total_payroll_usd: "1000.00",
        average_salary_usd: "10.00",
      })),
    };
    renderExplorer(many, {}, { by: "job_title", metric: "headcount" });

    expect(screen.getAllByRole("row")).toHaveLength(13);
    fireEvent.click(screen.getByRole("button", { name: "Show all 15 job titles" }));
    expect(screen.getAllByRole("row")).toHaveLength(16);
  });

  it("explains a single-row breakdown when the page is filtered to that dimension", () => {
    renderExplorer({ ...byCountry, rows: [byCountry.rows[1]] }, { country: "India" }, { by: "country", metric: "payroll" });

    expect(screen.getByText(/filtered to India, so this breakdown has a single row/)).toBeInTheDocument();
  });
});
