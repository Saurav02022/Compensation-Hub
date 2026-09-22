import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SummaryCards } from "./SummaryCards";

describe("SummaryCards", () => {
  it("shows the count, USD payroll and average, and the scope", () => {
    render(
      <SummaryCards
        scope="India · Engineering"
        summary={{ currency: "USD", employee_count: 10000, total_payroll_usd: "923456789.12", average_salary_usd: "92345.68" }}
      />,
    );

    expect(screen.getByText("10,000")).toBeInTheDocument();
    expect(screen.getByText("USD 923,456,789.12")).toBeInTheDocument();
    expect(screen.getByText("USD 92,345.68")).toBeInTheDocument();
    expect(screen.getByText("India · Engineering")).toBeInTheDocument();
    expect(screen.getAllByText("USD, normalized with seeded exchange rates")).toHaveLength(2);
  });

  it("shows a placeholder average when there are no salaries", () => {
    render(
      <SummaryCards
        summary={{ currency: "USD", employee_count: 0, total_payroll_usd: "0.00", average_salary_usd: null }}
      />,
    );

    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("No salaries to average")).toBeInTheDocument();
    expect(screen.getByText("Whole organization")).toBeInTheDocument();
  });
});
