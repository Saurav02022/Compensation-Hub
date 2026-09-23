import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CompensationPanel, type CompensationFormState } from "./CompensationPanel";

const compensation = { annual_salary: "62000.00", currency_code: "USD" };

type Action = (previous: CompensationFormState, formData: FormData) => Promise<CompensationFormState>;

describe("CompensationPanel", () => {
  it("shows the current salary and its currency, and opens the editor on request", async () => {
    const user = userEvent.setup();
    render(<CompensationPanel action={vi.fn()} compensation={compensation} />);

    expect(screen.getByText("62,000.00")).toBeInTheDocument();
    expect(screen.getByText(/Paid in US Dollar \(USD\)/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "New annual salary" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit salary" }));

    expect(screen.getByRole("textbox", { name: "New annual salary" })).toHaveValue("62000.00");
    expect(screen.getByRole("textbox", { name: "Currency" })).toHaveValue("USD");
    expect(screen.getByRole("button", { name: "Save salary" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("textbox", { name: "New annual salary" })).not.toBeInTheDocument();
  });

  it("previews the change, submits a plain decimal, and confirms the save", async () => {
    const user = userEvent.setup();
    const action = vi.fn<Action>(async () => ({ status: "success", message: "Salary updated" }));
    render(<CompensationPanel action={action} compensation={compensation} />);

    await user.click(screen.getByRole("button", { name: "Edit salary" }));
    const salary = screen.getByRole("textbox", { name: "New annual salary" });
    await user.clear(salary);
    await user.type(salary, "65,000");

    expect(screen.getByText("USD 62,000.00")).toBeInTheDocument();
    expect(screen.getByText("USD 65,000.00")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save salary" }));

    await waitFor(() => expect(action).toHaveBeenCalledTimes(1));
    expect(action.mock.calls[0][1].get("annual_salary")).toBe("65,000");
    expect(await screen.findByRole("status")).toHaveTextContent("Salary updated");
    expect(screen.queryByRole("textbox", { name: "New annual salary" })).not.toBeInTheDocument();
  });

  it("explains invalid input next to the field without calling the API", async () => {
    const user = userEvent.setup();
    const action = vi.fn<Action>();
    render(<CompensationPanel action={action} compensation={compensation} />);

    await user.click(screen.getByRole("button", { name: "Edit salary" }));
    const salary = screen.getByRole("textbox", { name: "New annual salary" });
    await user.clear(salary);
    await user.type(salary, "12k");
    await user.click(screen.getByRole("button", { name: "Save salary" }));

    expect(salary).toHaveAttribute("aria-invalid", "true");
    expect(salary).toHaveAccessibleDescription(/up to two decimal places/);
    expect(salary).toHaveFocus();
    expect(action).not.toHaveBeenCalled();
  });

  it("keeps the editor open and shows the error returned by the API", async () => {
    const user = userEvent.setup();
    const action = vi.fn<Action>(async () => ({ status: "error", message: "Currency XYZ is not supported" }));
    render(<CompensationPanel action={action} compensation={compensation} />);

    await user.click(screen.getByRole("button", { name: "Edit salary" }));
    const currency = screen.getByRole("textbox", { name: "Currency" });
    await user.clear(currency);
    await user.type(currency, "xyz");
    expect(currency).toHaveValue("XYZ");
    await user.click(screen.getByRole("button", { name: "Save salary" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Currency XYZ is not supported");
    expect(screen.getByRole("textbox", { name: "New annual salary" })).toBeInTheDocument();
  });

  it("opens the form immediately when there is no compensation on record", () => {
    render(<CompensationPanel action={vi.fn()} compensation={null} />);

    expect(screen.getByText(/No compensation on record yet/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Annual salary" })).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });
});
