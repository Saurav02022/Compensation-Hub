import { afterEach, describe, expect, it, vi } from "vitest";

import {
  analyticsHref,
  fetchBreakdown,
  fetchSummary,
  filtersFromSearchParams,
  viewFromSearchParams,
} from "./analytics";

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

  it("supports another sort key and a bounded limit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ rows: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchBreakdown("job_title", {}, { sortBy: "employee_count", limit: 5 });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://localhost:8000/analytics/breakdown?group_by=job_title&sort_by=employee_count&descending=true&limit=5",
    );
  });
});

describe("analyticsHref", () => {
  it("builds clean analytics URLs", () => {
    expect(analyticsHref({})).toBe("/analytics");
    expect(analyticsHref({ country: "United States", job_title: "Paralegal" })).toBe(
      "/analytics?country=United+States&job_title=Paralegal",
    );
  });

  it("adds a non-default breakdown view and omits the defaults", () => {
    expect(analyticsHref({ country: "India" }, { by: "department", metric: "average" })).toBe(
      "/analytics?country=India&by=department&metric=average",
    );
    expect(analyticsHref({}, { by: "country", metric: "payroll" })).toBe("/analytics");
  });
});

describe("viewFromSearchParams", () => {
  it("reads a supported view and falls back to the default for anything else", () => {
    expect(viewFromSearchParams({ by: "job_title", metric: "headcount" })).toEqual({ by: "job_title", metric: "headcount" });
    expect(viewFromSearchParams({ by: "salary; drop", metric: ["average", "payroll"] })).toEqual({
      by: "country",
      metric: "average",
    });
    expect(viewFromSearchParams({})).toEqual({ by: "country", metric: "payroll" });
  });
});
