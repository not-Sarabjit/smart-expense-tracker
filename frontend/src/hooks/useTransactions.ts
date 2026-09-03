import { useState, useEffect, useCallback } from "react";
import { getTransactions } from "../api/transactions";
import { extractErrorMessage } from "../utils/errorHandling";
import type { Transaction } from "../types";

interface UseTransactionsParams {
  year: number;
  month: number;
  isAllTime: boolean;
}

interface UseTransactionsResult {
  transactions: Transaction[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetches the transaction list for the given period.
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
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let data: Transaction[];

      if (isAllTime) {
        // No date filters — return everything sorted by date descending.
        data = await getTransactions({
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

        data = await getTransactions({
          start_date: startDate,
          end_date: endDate,
          sort_by: "date",
          sort_order: "desc",
        });
      }

      setTransactions(data);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load transactions."));
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [year, month, isAllTime]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  return { transactions, loading, error, refetch: fetchTransactions };
}
