import apiClient from "./client";
import type {
  Transaction,
  TransactionResponse,
  TransactionPage,
  TransactionCreatePayload,
  TransactionUpdatePayload,
  MonthlySummary,
} from "../types";

/** Largest page the backend accepts (`limit` ≤ 200). */
export const MAX_PAGE_SIZE = 200;

/** Safety cap for getAllTransactions so a huge history can't hang the UI. */
export const MAX_FETCH_ALL_ROWS = 5000;

export interface GetTransactionsParams {
  transaction_type?: "income" | "expense";
  category_id?: number;
  start_date?: string;
  end_date?: string;
  sort_by?: "date" | "amount";
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

/** Converts the API's Decimal-as-string amount to a number. */
export function normalizeTransaction(tx: TransactionResponse): Transaction {
  return { ...tx, amount: Number(tx.amount) };
}

/** Fetches one page of transactions plus the total match count (X-Total-Count). */
export function getTransactions(
  params?: GetTransactionsParams
): Promise<TransactionPage> {
  return apiClient
    .get<TransactionResponse[]>("/transactions", { params })
    .then((res) => {
      const items = res.data.map(normalizeTransaction);
      const header = res.headers?.["x-total-count"];
      const total = header !== undefined ? Number(header) : items.length;
      return { items, total: Number.isFinite(total) ? total : items.length };
    });
}

/**
 * Fetches every page matching the filters (up to MAX_FETCH_ALL_ROWS).
 * Used where the UI needs the full period, e.g. charts.
 */
export async function getAllTransactions(
  params?: Omit<GetTransactionsParams, "limit" | "offset">
): Promise<TransactionPage> {
  const items: Transaction[] = [];
  let total = 0;
  do {
    const page = await getTransactions({
      ...params,
      limit: MAX_PAGE_SIZE,
      offset: items.length,
    });
    items.push(...page.items);
    total = page.total;
    if (page.items.length === 0) break;
  } while (items.length < total && items.length < MAX_FETCH_ALL_ROWS);

  return { items, total };
}

export function createTransaction(
  payload: TransactionCreatePayload
): Promise<Transaction> {
  return apiClient
    .post<TransactionResponse>("/transactions", payload)
    .then((res) => normalizeTransaction(res.data));
}

export function updateTransaction(
  id: number,
  payload: TransactionUpdatePayload
): Promise<Transaction> {
  return apiClient
    .put<TransactionResponse>(`/transactions/${id}`, payload)
    .then((res) => normalizeTransaction(res.data));
}

export function deleteTransaction(id: number): Promise<void> {
  return apiClient.delete(`/transactions/${id}`).then(() => undefined);
}

export function getSummary(year: number, month: number): Promise<MonthlySummary> {
  return apiClient
    .get<MonthlySummary>("/transactions/summary", { params: { year, month } })
    .then((res) => ({
      income: Number(res.data.income),
      expense: Number(res.data.expense),
      net: Number(res.data.net),
    }));
}
