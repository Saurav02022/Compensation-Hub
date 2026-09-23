import { describe, expect, it } from "vitest";

import { formatAmount, formatSalary } from "./money";

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

describe("formatAmount", () => {
  it("formats the amount alone at the currency's precision", () => {
    expect(formatAmount("153000", "USD")).toBe("153,000.00");
    expect(formatAmount("9540000.00", "JPY")).toBe("9,540,000");
  });

  it("rounds to whole units for headline figures", () => {
    expect(formatAmount("889265556.49", "USD", { whole: true })).toBe("889,265,556");
  });

  it("returns unparsable values unchanged", () => {
    expect(formatAmount("n/a", "USD")).toBe("n/a");
  });
});
