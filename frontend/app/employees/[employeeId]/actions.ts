"use server";

import { revalidatePath } from "next/cache";

import { ApiError } from "@/lib/api/client";
import { updateCompensation } from "@/lib/api/employees";
import type { CompensationFormState } from "@/components/compensation/CompensationForm";

function fieldValue(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

export async function updateCompensationAction(
  employeeId: number,
  _previous: CompensationFormState,
  formData: FormData,
): Promise<CompensationFormState> {
  const payload = {
    annual_salary: fieldValue(formData, "annual_salary"),
    currency_code: fieldValue(formData, "currency_code").toUpperCase(),
  };

  try {
    await updateCompensation(employeeId, payload);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 422 || error.status === 404)) {
      return { status: "error", message: error.message };
    }
    return {
      status: "error",
      message: "The compensation could not be saved because the API is unavailable. Try again.",
    };
  }

  revalidatePath("/employees");
  revalidatePath(`/employees/${employeeId}`);
  return { status: "success", message: "Compensation updated." };
}
