import { createContext } from "react";
import type { User } from "../types";

/** Currency used before the profile has loaded (matches the backend default). */
export const DEFAULT_CURRENCY = "INR";

export interface CurrentUserContextValue {
  /** null until GET /users/me resolves (or if it failed) */
  user: User | null;
  loading: boolean;
  error: string | null;
  /** Re-fetch the profile from the server */
  refresh: () => Promise<void>;
  /** Replace the cached profile, e.g. with the PATCH /users/me response */
  setUser: (user: User) => void;
}

export const CurrentUserContext = createContext<CurrentUserContextValue>({
  user: null,
  loading: false,
  error: null,
  refresh: async () => {},
  setUser: () => {},
});
