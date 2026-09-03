import apiClient from "./client";
import type { AuthTokenResponse, User } from "../types";

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export function login(
  email: string,
  password: string
): Promise<AuthTokenResponse> {
  return apiClient
    .post<AuthTokenResponse>("/auth/login", { email, password })
    .then((res) => res.data);
}

export function register(payload: RegisterPayload): Promise<User> {
  return apiClient
    .post<User>("/auth/register", payload)
    .then((res) => res.data);
}
