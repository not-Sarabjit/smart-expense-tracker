import { useState, useEffect, useCallback } from "react";
import { getSummary } from "../api/transactions";
import { extractErrorMessage } from "../utils/errorHandling";
import type { MonthlySummary } from "../types";

interface UseDashboardSummaryParams {
  year: number;
  month: number;
  isAllTime: boolean;
}

interface UseDashboardSummaryResult {
  summary: MonthlySummary | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetches the monthly financial summary for the given year and month.
 * When `isAllTime` is true the API call is skipped and `summary` is null.
 * Re-fetches automatically whenever `year`, `month`, or `isAllTime` changes.
 */
export function useDashboardSummary({
  year,
  month,
  isAllTime,
}: UseDashboardSummaryParams): UseDashboardSummaryResult {
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    if (isAllTime) {
      // No summary endpoint for all-time view — reset state and skip the call.
      setSummary(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getSummary(year, month);
      setSummary(data);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load summary."));
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [year, month, isAllTime]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return { summary, loading, error, refetch: fetchSummary };
}
