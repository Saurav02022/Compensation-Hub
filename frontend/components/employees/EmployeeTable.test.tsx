import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Employee } from "@/types/employees";
import { EmployeeTable } from "./EmployeeTable";

const employees: Employee[] = [
  {
    id: 1,
    employee_code: "EMP00001",
    full_name: "Michael Nguyen",
    country: "United States",
    department: "Human Resources",
    job_title: "HR Coordinator",
    compensation: { annual_salary: "62000.00", currency_code: "USD" },
  },
  {
    id: 2,
    employee_code: "EMP00002",
    full_name: "Omar Joshi",
    country: "Australia",
    department: "Engineering",
    job_title: "Senior Software Engineer",
    compensation: null,
  },
];

describe("EmployeeTable", () => {
  it("renders one row per employee with the name linking to the detail page", () => {
    render(<EmployeeTable employees={employees} filtered={false} />);

    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Michael Nguyen" })).toHaveAttribute("href", "/employees/1");
    expect(screen.getByText("EMP00002")).toBeInTheDocument();
    expect(screen.getByText("USD 62,000.00")).toBeInTheDocument();
    expect(screen.getByText("Not on record")).toBeInTheDocument();
  });

  it("offers to clear filters when a filtered search has no results", () => {
    render(<EmployeeTable employees={[]} filtered />);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("No employees match");
    expect(screen.getByRole("link", { name: "Clear search and filters" })).toHaveAttribute("href", "/employees");
  });

  it("explains an empty dataset without offering to clear filters", () => {
    render(<EmployeeTable employees={[]} filtered={false} />);

    expect(screen.getByRole("status")).toHaveTextContent("No employees yet");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
