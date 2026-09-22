import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnalyticsFilters } from "./AnalyticsFilters";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh: vi.fn() }),
}));

const options = {
  countries: ["Germany", "India"],
  departments: ["Engineering", "Sales"],
  job_titles: ["Paralegal"],
};

describe("AnalyticsFilters", () => {
  beforeEach(() => replace.mockClear());

  it("applies a filter immediately and keeps the others", () => {
    render(<AnalyticsFilters filters={{ country: "India" }} options={options} />);

    fireEvent.change(screen.getByRole("combobox", { name: "Department" }), { target: { value: "Sales" } });

    expect(replace).toHaveBeenCalledWith("/analytics?country=India&department=Sales");
  });

  it("explains the scope and clears all filters", () => {
    render(<AnalyticsFilters filters={{ department: "Sales" }} options={options} />);

    expect(screen.getByRole("status")).toHaveTextContent("Filters apply to every metric and chart on this page.");
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));

    expect(replace).toHaveBeenCalledWith("/analytics");
  });

  it("describes the whole organization when nothing is filtered", () => {
    render(<AnalyticsFilters filters={{}} options={options} />);

    expect(screen.getByRole("status")).toHaveTextContent("Showing the whole organization.");
    expect(screen.queryByRole("button", { name: "Clear all" })).not.toBeInTheDocument();
  });
});
