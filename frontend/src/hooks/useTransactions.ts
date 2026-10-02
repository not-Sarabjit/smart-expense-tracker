import { useState, useEffect, useCallback } from "react";
import { getAllTransactions } from "../api/transactions";
import { extractErrorMessage } from "../utils/errorHandling";
import type { Transaction } from "../types";

interface UseTransactionsParams {
  year: number;
  month: number;
  isAllTime: boolean;
}

interface UseTransactionsResult {
  transactions: Transaction[];
  /** Total rows matching the period on the server (may exceed transactions.length at the fetch cap) */
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetches the full transaction list for the given period, paging through the
 * API (`limit`/`offset`, total from `X-Total-Count`) so charts see every row.
 *
 * When `isAllTime` is false the request is scoped to the calendar month:
 *   start_date = YYYY-MM-01, end_date = last day of that month.
 *
 * When `isAllTime` is true no date filters are applied; only the sort
 * parameters are sent.
 *
 * Re-fetches automatically whenever `year`, `month`, or `isAllTime` changes.
 */
export function useTransactions({
  year,
  month,
  isAllTime,
}: UseTransactionsParams): UseTransactionsResult {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let page;

      if (isAllTime) {
        // No date filters — return everything sorted by date descending.
        page = await getAllTransactions({
          sort_by: "date",
          sort_order: "desc",
        });
      } else {
        // Scope to the selected calendar month.
        // Using Date(year, month, 0) gives the last day of the previous month,
        // which is the last day of `month` (1-indexed).
        const paddedMonth = String(month).padStart(2, "0");
        const lastDay = new Date(year, month, 0).getDate();
        const startDate = `${year}-${paddedMonth}-01`;
        const endDate = `${year}-${paddedMonth}-${String(lastDay).padStart(2, "0")}`;

        page = await getAllTransactions({
          start_date: startDate,
          end_date: endDate,
          sort_by: "date",
          sort_order: "desc",
        });
      }

      setTransactions(page.items);
      setTotal(page.total);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load transactions."));
      setTransactions([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [year, month, isAllTime]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  return { transactions, total, loading, error, refetch: fetchTransactions };
}
