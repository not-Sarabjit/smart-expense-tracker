import apiClient from "./client";
import type { User, UserPreferencesUpdatePayload } from "../types";

/** GET /users/me — the signed-in user's profile and preferences. */
export function getMe(): Promise<User> {
  return apiClient.get<User>("/users/me").then((res) => res.data);
}

/** PATCH /users/me — update name and/or preferences; only sent fields change. */
export function updateMe(payload: UserPreferencesUpdatePayload): Promise<User> {
  return apiClient.patch<User>("/users/me", payload).then((res) => res.data);
}
