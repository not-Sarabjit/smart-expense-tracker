import { useState, useEffect, useCallback, useMemo, type ReactNode } from "react";
import { getMe } from "../api/users";
import { extractErrorMessage } from "../utils/errorHandling";
import { CurrentUserContext } from "./currentUserContext";
import type { User } from "../types";

/**
 * Loads the signed-in user's profile from GET /users/me once and shares it
 * (name, currency, timezone) with every authenticated page.
 * Mounted by ProtectedRoute, so it only runs when a token is present.
 */
export default function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setUser(await getMe());
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load your profile."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ user, loading, error, refresh, setUser }),
    [user, loading, error, refresh]
  );

  return <CurrentUserContext.Provider value={value}>{children}</CurrentUserContext.Provider>;
}
