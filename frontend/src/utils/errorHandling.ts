import axios from "axios";

export const NETWORK_ERROR_MESSAGE =
  "Unable to reach server. Please check your connection.";

/**
 * Extracts a human-readable error message from an unknown error value.
 * Handles both backend error shapes:
 *   - domain errors (AppException): `{ error: true, message, status_code }`
 *   - FastAPI defaults: `detail` as a string or an array of `{ msg }` objects
 * and requests that never got a response (network errors).
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
    if (!err.response) return NETWORK_ERROR_MESSAGE;
    const data = err.response.data;
    if (typeof data?.message === "string") return data.message;
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  }
  return fallback;
}
