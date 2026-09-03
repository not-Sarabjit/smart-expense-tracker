import apiClient from "./client";
import type {
  Transaction,
  TransactionCreatePayload,
  TransactionUpdatePayload,
  MonthlySummary,
} from "../types";

export interface GetTransactionsParams {
  start_date?: string;
  end_date?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export function getTransactions(
  params?: GetTransactionsParams
): Promise<Transaction[]> {
  return apiClient
    .get<Transaction[]>("/transactions", { params })
    .then((res) => res.data);
}

export function createTransaction(
  payload: TransactionCreatePayload
): Promise<Transaction> {
  return apiClient
    .post<Transaction>("/transactions", payload)
    .then((res) => res.data);
}

export function updateTransaction(
  id: number,
  payload: TransactionUpdatePayload
): Promise<Transaction> {
  return apiClient
    .put<Transaction>(`/transactions/${id}`, payload)
    .then((res) => res.data);
}

export function deleteTransaction(id: number): Promise<void> {
  return apiClient.delete(`/transactions/${id}`).then(() => undefined);
}

export function getSummary(year: number, month: number): Promise<MonthlySummary> {
  return apiClient
    .get<MonthlySummary>("/transactions/summary", { params: { year, month } })
    .then((res) => res.data);
}
