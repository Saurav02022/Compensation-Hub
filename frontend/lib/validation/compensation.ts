/*
 * Immediate feedback for the salary form. The API remains authoritative: it validates the amount,
 * its precision, and that the currency has an exchange rate on file.
 */

const SALARY_PATTERN = /^\d{1,12}(\.\d{1,2})?$/;
const CURRENCY_PATTERN = /^[A-Za-z]{3}$/;

/** Grouping separators and spaces are accepted while typing; the API receives a plain decimal. */
export function normalizeSalary(value: string): string {
  return value.replace(/[,\s]/g, "");
}

export function salaryError(value: string): string | undefined {
  const normalized = normalizeSalary(value);
  if (!normalized) return "Enter the annual salary.";
  if (!SALARY_PATTERN.test(normalized)) return "Use a positive amount with up to two decimal places, for example 65000.00.";
  if (Number(normalized) <= 0) return "The salary must be greater than zero.";
  return undefined;
}

export function currencyError(value: string): string | undefined {
  return CURRENCY_PATTERN.test(value.trim()) ? undefined : "Use a three-letter currency code, for example USD.";
}
