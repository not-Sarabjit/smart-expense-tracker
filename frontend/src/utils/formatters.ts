/**
 * Formats a number as a currency string with exactly two decimal places.
 * @param amount - The numeric amount to format
 * @param symbol - The currency symbol to prepend (defaults to "$")
 * @returns A string like "$1,234.56"
 */
export function formatCurrency(amount: number, symbol = "$"): string {
  const formatted = amount.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${symbol}${formatted}`;
}

/**
 * Formats an ISO date string to "MMM D, YYYY" format (e.g. "Jun 5, 2025").
 * @param isoString - A date string in ISO 8601 or "YYYY-MM-DD" format
 * @returns Formatted date string
 */
export function formatDate(isoString: string): string {
  // Parse "YYYY-MM-DD" without timezone shift by using the parts directly
  const [year, month, day] = isoString.slice(0, 10).split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
