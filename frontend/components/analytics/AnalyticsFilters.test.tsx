import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RouteTransitionProvider } from "@/components/ui/RouteTransition";
import type { AnalyticsView } from "@/lib/api/analytics";
import { resetRouter, router } from "@/test/router";
import type { AnalyticsFilters as Filters } from "@/types/analytics";
import { AnalyticsFilters } from "./AnalyticsFilters";

vi.mock("next/navigation", async () => {
  const { router: mockRouter } = await import("@/test/router");
  return { useRouter: () => mockRouter };
});

const options = {
  countries: ["Germany", "India"],
  departments: ["Engineering", "Sales"],
  job_titles: ["Paralegal"],
};

function renderFilters(filters: Filters, view: AnalyticsView = { by: "country", metric: "payroll" }) {
  return render(
    <RouteTransitionProvider>
      <AnalyticsFilters filters={filters} view={view} options={options} />
    </RouteTransitionProvider>,
  );
}

describe("AnalyticsFilters", () => {
  beforeEach(resetRouter);

  it("applies a filter immediately and keeps the other filters and the breakdown view", () => {
    renderFilters({ country: "India" }, { by: "job_title", metric: "average" });

    fireEvent.change(screen.getByRole("combobox", { name: "Department" }), { target: { value: "Sales" } });

    expect(router.replace).toHaveBeenCalledWith(
      "/analytics?country=India&department=Sales&by=job_title&metric=average",
      { scroll: false },
    );
  });

  it("removes a single filter or clears them all", () => {
    renderFilters({ country: "India", department: "Sales" });

    fireEvent.click(screen.getByRole("button", { name: "Remove country filter" }));
    expect(router.replace).toHaveBeenLastCalledWith("/analytics?department=Sales", { scroll: false });

    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
    expect(router.replace).toHaveBeenLastCalledWith("/analytics", { scroll: false });
  });

  it("offers no clear action when nothing is filtered", () => {
    renderFilters({});

    expect(screen.getByRole("combobox", { name: "Country" })).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Clear all" })).not.toBeInTheDocument();
  });
});
