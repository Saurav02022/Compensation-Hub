/**
 * Presentation-only formatting of a salary the API serialized as an exact decimal string.
 * The numeric conversion is used for display; it is never fed back into a calculation.
 */
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
