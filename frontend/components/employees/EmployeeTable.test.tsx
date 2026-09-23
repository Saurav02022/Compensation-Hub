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
    country: "Japan",
    department: "Engineering",
    job_title: "Senior Software Engineer",
    compensation: { annual_salary: "9540000.00", currency_code: "JPY" },
  },
  {
    id: 3,
    employee_code: "EMP00003",
    full_name: "Ana Silva",
    country: "Brazil",
    department: "Sales",
    job_title: "Account Executive",
    compensation: null,
  },
];

describe("EmployeeTable", () => {
  it("renders one row per employee, each opening the detail page", () => {
    render(<EmployeeTable employees={employees} filtered={false} />);

    expect(screen.getAllByRole("row")).toHaveLength(4);
    expect(screen.getByRole("link", { name: "Michael Nguyen" })).toHaveAttribute("href", "/employees/1");
    expect(screen.getByRole("rowheader", { name: /Omar Joshi/ })).toBeInTheDocument();
  });

  it("shows salaries in local currency at the precision of that currency", () => {
    render(<EmployeeTable employees={employees} filtered={false} />);

    const [michael, omar, ana] = screen.getAllByRole("row").slice(1);
    expect(michael).toHaveTextContent("62,000.00USD");
    expect(omar).toHaveTextContent("9,540,000JPY");
    expect(ana).toHaveTextContent("Not on record");
  });

  it("offers to clear search and filters when nothing matches", () => {
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

  it("links back to the first page when the requested page is past the end", () => {
    render(<EmployeeTable employees={[]} filtered outOfRange={{ firstPageHref: "/employees?country=India" }} />);

    expect(screen.getByRole("status")).toHaveTextContent("past the end of the results");
    expect(screen.getByRole("link", { name: "First page" })).toHaveAttribute("href", "/employees?country=India");
  });
});
