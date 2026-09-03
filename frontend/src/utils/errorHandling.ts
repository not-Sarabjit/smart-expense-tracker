import axios from "axios";

/**
 * Extracts a human-readable error message from an unknown error value.
 * Handles FastAPI's validation error format (detail as string or array of {msg} objects).
 *
 * @param err - The caught error value (unknown type)
 * @param fallback - Fallback message when no specific detail is available
 * @returns A displayable error string
 */
export function extractErrorMessage(
  err: unknown,
  fallback = "Something went wrong."
): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  }
  return fallback;
}
