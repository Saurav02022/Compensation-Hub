import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EmployeeToolbar } from "./EmployeeToolbar";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh: vi.fn() }),
}));

const options = {
  countries: ["India", "United States"],
  departments: ["Engineering", "Sales"],
  job_titles: ["Account Executive", "Software Engineer"],
};

describe("EmployeeToolbar", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    replace.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces search and navigates with the query, resetting the page", () => {
    render(<EmployeeToolbar query={{ page: 3, country: "India" }} options={options} />);

    const search = screen.getByRole("searchbox", { name: "Search" });
    fireEvent.change(search, { target: { value: "an" } });
    fireEvent.change(search, { target: { value: "ana" } });
    expect(replace).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/employees?search=ana&country=India");
  });

  it("applies a filter immediately and keeps the other filters", () => {
    render(<EmployeeToolbar query={{ page: 2, search: "ana", country: "India" }} options={options} />);

    fireEvent.change(screen.getByRole("combobox", { name: "Department" }), { target: { value: "Sales" } });

    expect(replace).toHaveBeenCalledWith("/employees?search=ana&country=India&department=Sales");
  });

  it("prefills the current query and clears everything at once", () => {
    render(<EmployeeToolbar query={{ page: 1, search: "emp0001", department: "Sales" }} options={options} />);

    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveValue("emp0001");
    expect(screen.getByRole("combobox", { name: "Department" })).toHaveValue("Sales");

    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));

    expect(replace).toHaveBeenCalledWith("/employees");
  });

  it("does not navigate when the search text is unchanged", () => {
    render(<EmployeeToolbar query={{ page: 1, search: "ana" }} options={options} />);

    fireEvent.change(screen.getByRole("searchbox", { name: "Search" }), { target: { value: "ana " } });
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(replace).not.toHaveBeenCalled();
  });
});
