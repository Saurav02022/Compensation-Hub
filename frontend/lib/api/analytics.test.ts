import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchBreakdown, fetchSummary, filtersFromSearchParams } from "./analytics";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("filtersFromSearchParams", () => {
  it("keeps only non-blank supported filters", () => {
    expect(
      filtersFromSearchParams({ country: "India", department: " ", job_title: undefined, page: "3" }),
    ).toEqual({ country: "India", department: undefined, job_title: undefined });
  });
});

describe("fetchSummary", () => {
  it("requests the summary without a query string when unfiltered", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        currency: "USD",
        employee_count: 0,
        total_payroll_usd: "0.00",
        average_salary_usd: null,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchSummary({});

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/analytics/summary");
  });

  it("passes filters through", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await fetchSummary({ country: "United States", department: "Sales" });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://localhost:8000/analytics/summary?country=United+States&department=Sales",
    );
  });
});

describe("fetchBreakdown", () => {
  it("requests the dimension sorted by payroll with the filters applied", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ rows: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchBreakdown("department", { country: "India" });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://localhost:8000/analytics/breakdown?country=India&group_by=department&sort_by=total_payroll_usd&descending=true",
    );
  });
});
