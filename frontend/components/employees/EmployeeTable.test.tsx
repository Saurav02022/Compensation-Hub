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
  it("renders one row per employee linking to the detail page", () => {
    render(<EmployeeTable employees={employees} />);

    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Michael Nguyen" })).toHaveAttribute(
      "href",
      "/employees/1",
    );
    expect(screen.getByRole("link", { name: "EMP00002" })).toHaveAttribute("href", "/employees/2");
    expect(screen.getByText("USD 62,000.00")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows an empty state when there are no employees", () => {
    render(<EmployeeTable employees={[]} />);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "No employees match the current search and filters.",
    );
  });
});
