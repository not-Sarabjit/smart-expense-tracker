import * as authApi from "../api/auth";
import type { RegisterPayload } from "../api/auth";
import type { User } from "../types";

/**
 * Custom hook that provides authentication helpers.
 * All state is persisted in localStorage so the hook is stateless
 * and safe to call from any component without a context provider.
 */
export function useAuth() {
  /**
   * Log in with email + password.
   * Stores access_token and user_profile in localStorage on success.
   * Throws on API error so the caller can surface it.
   */
  async function login(email: string, password: string): Promise<void> {
    const { access_token } = await authApi.login(email, password);
    localStorage.setItem("access_token", access_token);
    // login endpoint only returns the token; user_profile may have been
    // stored already during register. If not, store null to keep keys in sync.
    if (!localStorage.getItem("user_profile")) {
      localStorage.setItem("user_profile", "null");
    }
  }

  /**
   * Register a new account, then automatically log in with the same credentials.
   * Stores the User returned by the register endpoint so the Navbar can display
   * the user's name without a separate /users/me call.
   * Throws on API error so the caller can surface it.
   */
  async function register(payload: RegisterPayload): Promise<void> {
    const user: User = await authApi.register(payload);
    // Persist user profile before login so login() can find it.
    localStorage.setItem("user_profile", JSON.stringify(user));
    // Auto-login with same credentials.
    await login(payload.email, payload.password);
  }

  /**
   * Clear session data from localStorage.
   */
  function logout(): void {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_profile");
  }

  /**
   * Returns true when a non-empty access_token is present in localStorage.
   */
  function isAuthenticated(): boolean {
    const token = localStorage.getItem("access_token");
    return token !== null && token.length > 0;
  }

  return { login, register, logout, isAuthenticated };
}
