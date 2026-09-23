import { describe, expect, it } from "vitest";

import { currencyError, normalizeSalary, salaryError } from "./compensation";

describe("salary validation", () => {
  it("accepts plain and grouped amounts with up to two decimals", () => {
    expect(salaryError("65000")).toBeUndefined();
    expect(salaryError("65,000.50")).toBeUndefined();
    expect(normalizeSalary(" 1,250,000.00 ")).toBe("1250000.00");
  });

  it("explains empty, malformed, over-precise, and zero amounts", () => {
    expect(salaryError("")).toBe("Enter the annual salary.");
    expect(salaryError("12k")).toMatch(/up to two decimal places/);
    expect(salaryError("100.005")).toMatch(/up to two decimal places/);
    expect(salaryError("-5")).toMatch(/up to two decimal places/);
    expect(salaryError("0.00")).toBe("The salary must be greater than zero.");
  });
});

describe("currency validation", () => {
  it("requires a three-letter code", () => {
    expect(currencyError("usd")).toBeUndefined();
    expect(currencyError("US")).toMatch(/three-letter/);
    expect(currencyError("EURO")).toMatch(/three-letter/);
  });
});
