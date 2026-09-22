import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmployeeFilters } from "./EmployeeFilters";

const options = {
  countries: ["India", "United States"],
  departments: ["Engineering", "Sales"],
  job_titles: ["Account Executive", "Software Engineer"],
};

describe("EmployeeFilters", () => {
  it("submits as a GET form to the directory and offers every filter value", () => {
    render(<EmployeeFilters query={{ page: 1 }} options={options} />);

    const form = screen.getByRole("form", { name: "Employee filters" });
    expect(form).toHaveAttribute("method", "get");
    expect(form).toHaveAttribute("action", "/employees");
    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveValue("");
    expect(screen.getByRole("combobox", { name: "Country" })).toHaveValue("");
    expect(screen.getByRole("option", { name: "United States" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Software Engineer" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Clear" })).not.toBeInTheDocument();
  });

  it("prefills the current query and shows a clear link when filters are active", () => {
    render(
      <EmployeeFilters
        query={{ page: 2, search: "emp0001", country: "India", department: "Sales" }}
        options={options}
      />,
    );

    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveValue("emp0001");
    expect(screen.getByRole("combobox", { name: "Country" })).toHaveValue("India");
    expect(screen.getByRole("combobox", { name: "Department" })).toHaveValue("Sales");
    expect(screen.getByRole("combobox", { name: "Job title" })).toHaveValue("");
    expect(screen.getByRole("link", { name: "Clear" })).toHaveAttribute("href", "/employees");
  });
});
