import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import {
  employeeListSearchParams,
  fetchEmployee,
  fetchEmployees,
  queryFromSearchParams,
  updateCompensation,
} from "./employees";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("queryFromSearchParams", () => {
  it("reads page, search, and filters", () => {
    expect(
      queryFromSearchParams({
        page: "3",
        search: " Ana ",
        country: "India",
        department: "Engineering",
        job_title: "Staff Engineer",
      }),
    ).toEqual({
      page: 3,
      search: "Ana",
      country: "India",
      department: "Engineering",
      job_title: "Staff Engineer",
    });
  });

  it("falls back to page 1 for malformed or missing pages and drops blank values", () => {
    expect(queryFromSearchParams({ page: "abc", search: "  ", country: "" })).toEqual({
      page: 1,
      search: undefined,
      country: undefined,
      department: undefined,
      job_title: undefined,
    });
    expect(queryFromSearchParams({ page: "-2" }).page).toBe(1);
    expect(queryFromSearchParams({ page: ["7", "8"] }).page).toBe(7);
  });
});

describe("employeeListSearchParams", () => {
  it("omits the first page and empty values", () => {
    expect(employeeListSearchParams({ page: 1, search: undefined }).toString()).toBe("");
  });

  it("encodes every provided value", () => {
    const params = employeeListSearchParams({
      page: 2,
      search: "O'Brien & co",
      country: "United States",
      department: "Sales",
      job_title: "Account Executive",
    });
    expect(params.get("page")).toBe("2");
    expect(params.get("search")).toBe("O'Brien & co");
    expect(params.toString()).toContain("country=United+States");
  });
});

describe("fetchEmployees", () => {
  it("requests the employees endpoint with the query and returns the page", async () => {
    const page = { items: [], page: 2, page_size: 25, total_items: 0, total_pages: 1 };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(page));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchEmployees({ page: 2, country: "India" })).resolves.toEqual(page);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/employees?page=2&country=India");
  });
});

describe("fetchEmployee", () => {
  it("throws an ApiError carrying the status and message when the API rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Employee 42 not found" }, 404)),
    );

    const error = await fetchEmployee(42).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).message).toBe("Employee 42 not found");
  });
});

describe("updateCompensation", () => {
  it("sends a PATCH with the salary as an exact string", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ annual_salary: "123456.78", currency_code: "USD" }));
    vi.stubGlobal("fetch", fetchMock);

    await updateCompensation(7, { annual_salary: "123456.78", currency_code: "USD" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/employees/7/compensation");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe('{"annual_salary":"123456.78","currency_code":"USD"}');
  });

  it("summarizes field validation errors from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            detail: [
              { loc: ["body", "annual_salary"], msg: "Input should be greater than 0" },
            ],
          },
          422,
        ),
      ),
    );

    const error = (await updateCompensation(7, { annual_salary: "-1", currency_code: "USD" }).catch(
      (e: unknown) => e,
    )) as ApiError;

    expect(error.message).toBe("Annual salary: Input should be greater than 0");
  });
});
