import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SummaryMetrics, describeScope } from "./SummaryMetrics";

describe("SummaryMetrics", () => {
  it("shows the headline figures rounded to whole units with the exact amounts on hover", () => {
    render(
      <SummaryMetrics
        scope="India · Engineering"
        summary={{ currency: "USD", employee_count: 10000, total_payroll_usd: "923456789.12", average_salary_usd: "92345.68" }}
      />,
    );

    expect(screen.getByText("10,000")).toBeInTheDocument();
    expect(screen.getByText("923,456,789").closest("dd")).toHaveAttribute("title", "923456789.12 USD");
    expect(screen.getByText("92,346").closest("dd")).toHaveAttribute("title", "92345.68 USD");
    expect(screen.getByText("India · Engineering")).toBeInTheDocument();
  });

  it("shows a placeholder average when there are no salaries", () => {
    render(
      <SummaryMetrics
        scope="Whole organization"
        summary={{ currency: "USD", employee_count: 0, total_payroll_usd: "0.00", average_salary_usd: null }}
      />,
    );

    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("No salaries to average")).toBeInTheDocument();
  });

  it("describes the filter scope", () => {
    expect(describeScope({})).toBe("Whole organization");
    expect(describeScope({ country: "India", job_title: "Paralegal" })).toBe("India · Paralegal");
  });
});
