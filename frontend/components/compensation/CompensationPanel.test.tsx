import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CompensationPanel, type CompensationFormState } from "./CompensationPanel";

const compensation = { annual_salary: "62000.00", currency_code: "USD" };

describe("CompensationPanel", () => {
  it("shows the current salary and reveals the edit form on demand", async () => {
    render(<CompensationPanel action={vi.fn()} compensation={compensation} />);

    expect(screen.getByText("USD 62,000.00")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Annual salary" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByRole("textbox", { name: "Annual salary" })).toHaveValue("62000.00");
    expect(screen.getByRole("textbox", { name: "Currency code" })).toHaveValue("USD");

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("textbox", { name: "Annual salary" })).not.toBeInTheDocument();
  });

  it("submits the edited values and shows the saved message", async () => {
    const action = vi.fn<(previous: CompensationFormState, formData: FormData) => Promise<CompensationFormState>>(
      async () => ({ status: "success", message: "Compensation updated." }),
    );
    render(<CompensationPanel action={action} compensation={compensation} />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    const salary = screen.getByRole("textbox", { name: "Annual salary" });
    await user.clear(salary);
    await user.type(salary, "65000.00");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(action).toHaveBeenCalledTimes(1));
    expect(action.mock.calls[0][1].get("annual_salary")).toBe("65000.00");
    expect(await screen.findByRole("status")).toHaveTextContent("Compensation updated.");
    expect(screen.queryByRole("textbox", { name: "Annual salary" })).not.toBeInTheDocument();
  });

  it("keeps the form open and shows the error returned by the action", async () => {
    const action = vi.fn(async (): Promise<CompensationFormState> => ({
      status: "error",
      message: "Currency XYZ is not supported",
    }));
    render(<CompensationPanel action={action} compensation={compensation} />);

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Currency XYZ is not supported");
    expect(screen.getByRole("textbox", { name: "Annual salary" })).toBeInTheDocument();
  });

  it("opens the form immediately when there is no compensation on record", () => {
    render(<CompensationPanel action={vi.fn()} compensation={null} />);

    expect(screen.getByText("No compensation on record for this employee.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Annual salary" })).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });
});
