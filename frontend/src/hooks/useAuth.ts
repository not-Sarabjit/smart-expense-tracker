import * as authApi from "../api/auth";
import type { RegisterPayload } from "../api/auth";

/** Legacy key from before GET /users/me existed — only removed now, never written. */
const LEGACY_PROFILE_KEY = "user_profile";

/**
 * Custom hook that provides authentication helpers.
 * All state is persisted in localStorage so the hook is stateless
 * and safe to call from any component without a context provider.
 */
export function useAuth() {
  /**
   * Log in with email + password.
   * Stores access_token in localStorage on success; the profile itself is
   * loaded from GET /users/me by CurrentUserProvider.
   * Throws on API error so the caller can surface it.
   */
  async function login(email: string, password: string): Promise<void> {
    const { access_token } = await authApi.login(email, password);
    localStorage.setItem("access_token", access_token);
    localStorage.removeItem(LEGACY_PROFILE_KEY);
  }

  /**
   * Register a new account, then automatically log in with the same credentials.
   * Throws on API error so the caller can surface it.
   */
  async function register(payload: RegisterPayload): Promise<void> {
    await authApi.register(payload);
    // Auto-login with same credentials.
    await login(payload.email, payload.password);
  }

  /**
   * Clear session data from localStorage.
   */
  function logout(): void {
    localStorage.removeItem("access_token");
    localStorage.removeItem(LEGACY_PROFILE_KEY);
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
