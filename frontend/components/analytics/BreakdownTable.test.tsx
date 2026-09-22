import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BreakdownTable } from "./BreakdownTable";

describe("BreakdownTable", () => {
  it("renders one row per group with currency-labelled columns", () => {
    render(
      <BreakdownTable
        caption="Exact values by country"
        breakdown={{
          group_by: "country",
          currency: "USD",
          rows: [
            { key: "United States", employee_count: 2570, total_payroll_usd: "306210500.00", average_salary_usd: "119147.28" },
            { key: "India", employee_count: 1967, total_payroll_usd: "70658280.00", average_salary_usd: "35921.85" },
          ],
        }}
      />,
    );

    expect(screen.getByRole("table", { name: "Exact values by country" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Total payroll (USD)" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "United States" })).toBeInTheDocument();
    expect(screen.getByText("USD 306,210,500.00")).toBeInTheDocument();
    expect(screen.getByText("2,570")).toBeInTheDocument();
  });

  it("shows an empty state when there are no rows", () => {
    render(<BreakdownTable caption="Exact values" breakdown={{ group_by: "job_title", currency: "USD", rows: [] }} />);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("No employees match the current filters.");
  });
});
