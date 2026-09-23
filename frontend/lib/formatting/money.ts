/*
 * Presentation-only formatting of amounts the API serialized as exact decimal strings.
 * The numeric conversion is used for display; it is never fed back into a calculation.
 */

function currencyDigits(currencyCode: string): number {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: currencyCode }).resolvedOptions()
      .maximumFractionDigits ?? 2;
  } catch {
    return 2;
  }
}

/** "USD 153,000.00" — the amount with its currency code, at the currency's usual precision. */
export function formatSalary(annualSalary: string, currencyCode: string): string {
  const amount = Number(annualSalary);
  if (!Number.isFinite(amount)) {
    return `${annualSalary} ${currencyCode}`;
  }
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode,
      currencyDisplay: "code",
    }).format(amount);
  } catch {
    return `${annualSalary} ${currencyCode}`;
  }
}

/** "153,000.00" — the amount alone, for columns and figures that state the currency separately. */
export function formatAmount(value: string, currencyCode: string, options: { whole?: boolean } = {}): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return value;
  }
  const digits = options.whole ? 0 : currencyDigits(currencyCode);
  return new Intl.NumberFormat("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(amount);
}

export function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}
