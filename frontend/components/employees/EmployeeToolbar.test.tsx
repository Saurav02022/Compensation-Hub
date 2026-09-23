import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RouteTransitionProvider } from "@/components/ui/RouteTransition";
import { resetRouter, router } from "@/test/router";
import type { EmployeeListQuery } from "@/types/employees";
import { EmployeeToolbar } from "./EmployeeToolbar";

vi.mock("next/navigation", async () => {
  const { router: mockRouter } = await import("@/test/router");
  return { useRouter: () => mockRouter };
});

const options = {
  countries: ["India", "United States"],
  departments: ["Engineering", "Sales"],
  job_titles: ["Account Executive", "Software Engineer"],
};

function renderToolbar(query: EmployeeListQuery) {
  return render(
    <RouteTransitionProvider>
      <EmployeeToolbar query={query} options={options} />
    </RouteTransitionProvider>,
  );
}

describe("EmployeeToolbar", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetRouter();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces search into one navigation that keeps filters and resets the page", () => {
    renderToolbar({ page: 3, country: "India" });

    const search = screen.getByRole("searchbox", { name: "Search" });
    fireEvent.change(search, { target: { value: "an" } });
    fireEvent.change(search, { target: { value: "ana" } });
    act(() => {
      vi.advanceTimersByTime(299);
    });
    expect(router.replace).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledWith("/employees?search=ana&country=India", { scroll: false });
  });

  it("applies a filter immediately, keeping the search and other filters", () => {
    renderToolbar({ page: 2, search: "ana", country: "India" });

    fireEvent.change(screen.getByRole("combobox", { name: "Department" }), { target: { value: "Sales" } });

    expect(router.replace).toHaveBeenCalledWith("/employees?search=ana&country=India&department=Sales", {
      scroll: false,
    });
  });

  it("shows active filters and removes one without touching the rest", () => {
    renderToolbar({ page: 1, country: "India", department: "Sales" });

    expect(screen.getByRole("combobox", { name: "Country" })).toHaveValue("India");
    fireEvent.click(screen.getByRole("button", { name: "Remove country filter" }));

    expect(router.replace).toHaveBeenCalledWith("/employees?department=Sales", { scroll: false });
  });

  it("clears the search and every filter at once", () => {
    renderToolbar({ page: 1, search: "emp0001", department: "Sales" });

    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveValue("emp0001");
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));

    expect(router.replace).toHaveBeenCalledWith("/employees", { scroll: false });
  });

  it("does not navigate when the trimmed search is unchanged", () => {
    renderToolbar({ page: 1, search: "ana" });

    fireEvent.change(screen.getByRole("searchbox", { name: "Search" }), { target: { value: "ana " } });
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(router.replace).not.toHaveBeenCalled();
  });

  it("focuses the search box with the slash key", () => {
    renderToolbar({ page: 1 });

    fireEvent.keyDown(window, { key: "/" });

    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveFocus();
  });
});
