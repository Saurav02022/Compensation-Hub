import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Pagination } from "./Pagination";

describe("Pagination", () => {
  it("shows the result range and links to neighbouring pages while preserving filters", () => {
    render(
      <Pagination
        query={{ page: 3, search: "ana", country: "India" }}
        page={3}
        pageSize={25}
        totalPages={10}
        totalItems={247}
      />,
    );

    expect(screen.getByText("Showing 51–75 of 247")).toBeInTheDocument();
    expect(screen.getByText("Page 3 of 10")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Previous" })).toHaveAttribute(
      "href",
      "/employees?page=2&search=ana&country=India",
    );
    expect(screen.getByRole("link", { name: "Next" })).toHaveAttribute(
      "href",
      "/employees?page=4&search=ana&country=India",
    );
  });

  it("disables previous on the first page and next on the last page", () => {
    render(<Pagination query={{ page: 1 }} page={1} pageSize={25} totalPages={1} totalItems={12} />);

    expect(screen.queryByRole("link", { name: "Previous" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Next" })).not.toBeInTheDocument();
    expect(screen.getByText("Previous")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Showing 1–12 of 12")).toBeInTheDocument();
  });

  it("drops the page parameter when linking back to the first page", () => {
    render(<Pagination query={{ page: 2 }} page={2} pageSize={25} totalPages={2} totalItems={30} />);

    expect(screen.getByRole("link", { name: "Previous" })).toHaveAttribute("href", "/employees");
    expect(screen.getByText("Showing 26–30 of 30")).toBeInTheDocument();
  });
});
