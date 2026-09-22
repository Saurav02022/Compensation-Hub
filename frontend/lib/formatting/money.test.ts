import { describe, expect, it } from "vitest";

import { formatSalary } from "./money";

describe("formatSalary", () => {
  // Intl separates the currency code from the amount with a non-breaking space.
  it("formats amounts with the currency code and grouping", () => {
    expect(formatSalary("123456.78", "USD")).toBe("USD 123,456.78");
    expect(formatSalary("2400000.00", "INR")).toBe("INR 2,400,000.00");
  });

  it("respects currencies without minor units", () => {
    expect(formatSalary("12650000.00", "JPY")).toBe("JPY 12,650,000");
  });

  it("falls back to the raw value for unknown currencies or unparsable amounts", () => {
    expect(formatSalary("100", "ZZZZ")).toBe("100 ZZZZ");
    expect(formatSalary("abc", "USD")).toBe("abc USD");
  });
});
