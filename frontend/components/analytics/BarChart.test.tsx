import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BarChart } from "./BarChart";

const rows = [
  { key: "United States", magnitude: 306210500, display: "USD 306,210,500.00", detail: "2,570 employees", href: "/analytics?country=United+States" },
  { key: "India", magnitude: 70658280, display: "USD 70,658,280.00", detail: "1,967 employees", href: "/analytics?country=India", selected: true },
];

describe("BarChart", () => {
  it("renders a bar per row sized against the largest value, with linked labels and exact values", () => {
    render(<BarChart title="Total payroll by country" rows={rows} dimensionLabel="Country" valueLabel="Total payroll" />);

    expect(screen.getByRole("heading", { name: "Total payroll by country" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "United States" })).toHaveAttribute("href", "/analytics?country=United+States");
    expect(screen.getByText("USD 306,210,500.00")).toBeInTheDocument();
    expect(screen.getByText("Selected")).toBeInTheDocument();

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveAttribute("title", "United States: USD 306,210,500.00 (2,570 employees)");
    const bars = items.map((item) => item.querySelector("[aria-hidden='true']") as HTMLElement);
    expect(bars[0].style.width).toBe("100%");
    expect(Number.parseFloat(bars[1].style.width)).toBeCloseTo(23.07, 1);
  });

  it("shows the first rows and folds the rest behind a disclosure", () => {
    const many = Array.from({ length: 12 }, (_, index) => ({
      key: `Role ${index + 1}`,
      magnitude: 12 - index,
      display: String(12 - index),
    }));
    render(<BarChart title="Headcount by job title" rows={many} dimensionLabel="Job title" valueLabel="Employees" initialCount={10} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(12);
    expect(screen.getByText("Show all 12")).toBeInTheDocument();
    expect(screen.getByText("Role 12").closest("details")).not.toBeNull();
    expect(screen.getByText("Role 1").closest("details")).toBeNull();
  });

  it("shows an empty message when there are no rows", () => {
    render(<BarChart title="Average salary by department" rows={[]} dimensionLabel="Department" valueLabel="Average salary" />);

    expect(screen.getByRole("status")).toHaveTextContent("No employees match the current filters.");
  });
});
