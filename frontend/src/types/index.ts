export type TransactionType = "income" | "expense";
export type CategoryType = "income" | "expense";

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string | null;
  currency: string; // ISO 4217, e.g. "INR"
  timezone: string; // IANA, e.g. "Asia/Kolkata"
  created_at: string; // ISO 8601
}

/** PATCH /users/me body — only the fields sent are changed (email is not editable). */
export interface UserPreferencesUpdatePayload {
  first_name?: string;
  last_name?: string;
  currency?: string;
  timezone?: string;
}

export interface Category {
  id: number;
  name: string;
  category_type: CategoryType;
  /** null = built-in default category (read-only); otherwise the owner's id */
  user_id: number | null;
}

/** Transaction exactly as the API sends it — `amount` is a Decimal serialised as a string. */
export interface TransactionResponse {
  id: number;
  amount: string; // e.g. "42.50"
  date: string; // "YYYY-MM-DD"
  type: TransactionType;
  category_id: number | null;
  description: string | null;
  created_at: string;
  updated_at: string | null;
}

/** Transaction as used inside the app — `amount` normalised to a number by the API layer. */
export interface Transaction extends Omit<TransactionResponse, "amount"> {
  amount: number;
}

/** One page of transactions; `total` comes from the X-Total-Count response header. */
export interface TransactionPage {
  items: Transaction[];
  total: number;
}

/** GET /transactions/summary response */
export interface MonthlySummary {
  income: number;
  expense: number;
  net: number;
}

export interface AuthTokenResponse {
  access_token: string;
}

// --- Request payloads ---

export interface TransactionCreatePayload {
  amount: number;
  date: string; // "YYYY-MM-DD"
  type: TransactionType;
  category_id: number | null;
  description?: string | null;
}

export type TransactionUpdatePayload = Partial<TransactionCreatePayload>;

export interface CategoryCreatePayload {
  name: string;
  category_type: CategoryType;
}

export type CategoryUpdatePayload = Partial<CategoryCreatePayload>;

// --- Chat ---

export * from "./chat";
