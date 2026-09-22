import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CompensationForm, type CompensationFormState } from "./CompensationForm";

const compensation = { annual_salary: "62000.00", currency_code: "USD" };

describe("CompensationForm", () => {
  it("prefills the current compensation and submits the edited values", async () => {
    const action = vi.fn<
      (previous: CompensationFormState, formData: FormData) => Promise<CompensationFormState>
    >(async () => ({ status: "success", message: "Compensation updated." }));
    render(<CompensationForm action={action} compensation={compensation} />);

    const salary = screen.getByRole("textbox", { name: "Annual salary" });
    expect(salary).toHaveValue("62000.00");
    expect(screen.getByRole("textbox", { name: "Currency code" })).toHaveValue("USD");

    const user = userEvent.setup();
    await user.clear(salary);
    await user.type(salary, "65000.00");
    await user.click(screen.getByRole("button", { name: "Save compensation" }));

    await waitFor(() => expect(action).toHaveBeenCalledTimes(1));
    const formData = action.mock.calls[0][1];
    expect(formData.get("annual_salary")).toBe("65000.00");
    expect(formData.get("currency_code")).toBe("USD");
    expect(await screen.findByRole("status")).toHaveTextContent("Compensation updated.");
  });

  it("shows the error returned by the action", async () => {
    const action = vi.fn(async (): Promise<CompensationFormState> => ({
      status: "error",
      message: "Currency XYZ is not supported",
    }));
    render(<CompensationForm action={action} compensation={compensation} />);

    await userEvent.click(screen.getByRole("button", { name: "Save compensation" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Currency XYZ is not supported");
  });

  it("renders empty fields when the employee has no compensation", () => {
    const action = vi.fn(async (): Promise<CompensationFormState> => ({ status: "idle", message: "" }));
    render(<CompensationForm action={action} compensation={null} />);

    expect(screen.getByRole("textbox", { name: "Annual salary" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Currency code" })).toHaveValue("");
  });
});
