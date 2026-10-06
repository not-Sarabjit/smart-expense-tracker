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

/**
 * Formats an amount in the given ISO 4217 currency, e.g. formatMoney(1234.5, "INR") → "₹1,234.50".
 * Falls back to "<CODE> 1,234.50" if the runtime doesn't know the currency code.
 * @param amount - The numeric amount to format
 * @param currency - ISO 4217 currency code (the user's preference from /users/me)
 */
export function formatMoney(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return formatCurrency(amount, `${currency} `);
  }
}

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

/**
 * Formats an ISO timestamp relative to `now`, e.g. "5 minutes ago", "yesterday".
 * Anything under a minute old is "just now"; an unparseable input is returned as-is.
 * @param isoString - ISO 8601 timestamp
 * @param now - Reference time in ms (defaults to Date.now(); injectable for tests)
 */
export function formatRelativeTime(isoString: string, now: number = Date.now()): string {
  const time = Date.parse(isoString);
  if (Number.isNaN(time)) return isoString;
  const seconds = Math.round((time - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });
  for (const [unit, size] of RELATIVE_UNITS) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.trunc(seconds / size), unit);
  }
  return "just now";
}
