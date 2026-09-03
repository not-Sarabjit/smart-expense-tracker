export type TransactionType = "income" | "expense";
export type CategoryType = "income" | "expense";

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  created_at: string; // ISO 8601
}

export interface Category {
  id: number;
  name: string;
  category_type: CategoryType;
  user_id: number;
}

export interface Transaction {
  id: number;
  amount: number; // Decimal serialised as number by FastAPI
  date: string; // "YYYY-MM-DD"
  type: TransactionType; // aliased from "transaction_type" by backend
  category_id: number;
  description: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface MonthlySummary {
  total_income: number;
  total_expense: number;
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
  category_id: number;
  description?: string | null;
}

export interface TransactionUpdatePayload extends Partial<TransactionCreatePayload> {}

export interface CategoryCreatePayload {
  name: string;
  category_type: CategoryType;
}

export interface CategoryUpdatePayload extends Partial<CategoryCreatePayload> {}
