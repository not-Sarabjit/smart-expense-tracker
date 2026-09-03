import { useState, useEffect, useCallback } from "react";
import { getCategories } from "../api/categories";
import { extractErrorMessage } from "../utils/errorHandling";
import type { Category } from "../types";

interface UseCategoriesResult {
  categories: Category[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetches all user categories from `GET /categories/` on mount.
 * Exposes a `refetch` callback to re-fetch manually after mutations.
 *
 * Shared between DashboardPage (for category name resolution in the
 * transaction list) and CategoriesPage (full CRUD management).
 */
export function useCategories(): UseCategoriesResult {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCategories = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getCategories();
      setCategories(data);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load categories."));
      setCategories([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  return { categories, loading, error, refetch: fetchCategories };
}
