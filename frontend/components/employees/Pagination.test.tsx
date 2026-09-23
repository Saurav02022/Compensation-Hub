import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RouteTransitionProvider } from "@/components/ui/RouteTransition";
import { resetRouter, router } from "@/test/router";
import { Pagination } from "./Pagination";

vi.mock("next/navigation", async () => {
  const { router: mockRouter } = await import("@/test/router");
  return { useRouter: () => mockRouter };
});

function renderPagination(props: Parameters<typeof Pagination>[0]) {
  return render(
    <RouteTransitionProvider>
      <Pagination {...props} />
    </RouteTransitionProvider>,
  );
}

describe("Pagination", () => {
  beforeEach(resetRouter);

  it("shows the result range and links to neighbouring pages while preserving filters", () => {
    renderPagination({
      query: { page: 3, search: "ana", country: "India" },
      page: 3,
      pageSize: 25,
      totalPages: 10,
      totalItems: 247,
    });

    expect(screen.getByRole("navigation", { name: "Pagination" })).toHaveTextContent("51–75 of 247");
    expect(screen.getByText("Page 3 of 10")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Previous page" })).toHaveAttribute(
      "href",
      "/employees?page=2&search=ana&country=India",
    );
    expect(screen.getByRole("link", { name: "Next page" })).toHaveAttribute(
      "href",
      "/employees?page=4&search=ana&country=India",
    );
  });

  it("navigates inside the shared transition so the current page stays visible", () => {
    renderPagination({ query: { page: 1 }, page: 1, pageSize: 25, totalPages: 2, totalItems: 30 });

    fireEvent.click(screen.getByRole("link", { name: "Next page" }));

    expect(router.push).toHaveBeenCalledWith("/employees?page=2");
  });

  it("disables previous on the first page and next on the last page", () => {
    renderPagination({ query: { page: 1 }, page: 1, pageSize: 25, totalPages: 1, totalItems: 12 });

    expect(screen.getByRole("link", { name: "Previous page" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("link", { name: "Next page" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("navigation", { name: "Pagination" })).toHaveTextContent("1–12 of 12");
  });

  it("drops the page parameter when linking back to the first page", () => {
    renderPagination({ query: { page: 2 }, page: 2, pageSize: 25, totalPages: 2, totalItems: 30 });

    expect(screen.getByRole("link", { name: "Previous page" })).toHaveAttribute("href", "/employees");
    expect(screen.getByRole("navigation", { name: "Pagination" })).toHaveTextContent("26–30 of 30");
  });
});
