import { useContext } from "react";
import {
  CurrentUserContext,
  DEFAULT_CURRENCY,
  type CurrentUserContextValue,
} from "../context/currentUserContext";

/** The signed-in user's profile (from GET /users/me) plus refresh/setUser helpers. */
export function useCurrentUser(): CurrentUserContextValue {
  return useContext(CurrentUserContext);
}

/** The user's preferred ISO 4217 currency code, e.g. "INR". */
export function useCurrency(): string {
  return useContext(CurrentUserContext).user?.currency ?? DEFAULT_CURRENCY;
}
