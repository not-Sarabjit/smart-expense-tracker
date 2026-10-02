import { useState, useEffect } from "react";
import { Transaction, Category } from "@/types";
import { formatCurrency, formatDate } from "@/utils/formatters";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { deleteTransaction } from "@/api/transactions";
import { extractErrorMessage } from "@/utils/errorHandling";

export interface TransactionListProps {
  transactions: Transaction[];
  /** Total rows on the server for this period (defaults to transactions.length) */
  total?: number;
  categories: Category[];
  loading: boolean;
  error: string | null;
  onEdit: (tx: Transaction) => void;
  /** Called after a successful delete so the parent can refetch data */
  onDelete: (tx: Transaction) => void;
}

/** Number of skeleton rows to show while loading */
const SKELETON_ROW_COUNT = 5;

/** Rows rendered per "Show more" click */
export const LIST_PAGE_SIZE = 50;

/**
 * Displays a list of transactions with date, description, category, and
 * colour-coded amount. Handles loading, empty, and error states.
 *
 * Delete button on each row opens a ConfirmModal; on 204 calls onDelete so
 * the parent can refetch. (Requirements 10.1–10.7)
 *
 * Requirements: 8.2, 8.3, 8.4, 8.5, 8.7, 8.8, 10.1–10.7
 */
export function TransactionList({
  transactions,
  total,
  categories,
  loading,
  error,
  onEdit,
  onDelete,
}: TransactionListProps) {
  // Build a fast lookup map: category id → name
  const categoryMap = new Map<number, string>(
    categories.map((c) => [c.id, c.name])
  );

  // ── Client-side paging: render LIST_PAGE_SIZE rows at a time ───────────────
  const [visibleCount, setVisibleCount] = useState(LIST_PAGE_SIZE);
  useEffect(() => {
    setVisibleCount(LIST_PAGE_SIZE);
  }, [transactions]);
  const visibleTransactions = transactions.slice(0, visibleCount);
  const serverTotal = total ?? transactions.length;

  // ── Delete confirmation state ──────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<Transaction | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleConfirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteTransaction(deleteTarget.id);
      // On 204: close modal and notify parent to refetch (Req 10.5)
      setDeleteTarget(null);
      onDelete(deleteTarget);
    } catch (err: unknown) {
      // Display inline error in ConfirmModal without closing it (Req 10.7)
      setDeleteError(
        extractErrorMessage(err, "Failed to delete transaction. Please try again.")
      );
    } finally {
      setDeleting(false);
    }
  }

  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        role="status"
        aria-label="Loading transactions"
        className="rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden"
      >
        {Array.from({ length: SKELETON_ROW_COUNT }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-3 px-4 py-3 border-b last:border-b-0
                       border-gray-100 dark:border-gray-700
                       bg-white dark:bg-gray-800"
          >
            {/* date skeleton */}
            <div className="h-4 w-20 shrink-0 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
            {/* description skeleton — flex-1 but won't overflow */}
            <div className="h-4 flex-1 min-w-0 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
            {/* category skeleton — hidden on mobile */}
            <div className="hidden sm:block h-4 w-20 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
            {/* amount skeleton */}
            <div className="h-4 w-14 shrink-0 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
            {/* delete button skeleton */}
            <div className="h-6 w-6 shrink-0 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
          </div>
        ))}
        {/* Screen-reader spinner */}
        <span className="sr-only">
          <LoadingSpinner />
        </span>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-200 dark:border-red-700
                   bg-red-50 dark:bg-red-900/30 px-4 py-3
                   text-sm text-red-600 dark:text-red-400"
      >
        {error}
      </div>
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────────
  if (transactions.length === 0) {
    return (
      <EmptyState message="No transactions found for this period." />
    );
  }

  // ── Populated list ─────────────────────────────────────────────────────────
  return (
    <>
      <div className="rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden">
        {/* Header row — hide description and category columns on small screens */}
        <div
          className="hidden sm:grid sm:grid-cols-[1fr_2fr_1fr_1fr_auto] gap-4 px-4 py-2
                     bg-gray-50 dark:bg-gray-900
                     text-xs font-semibold uppercase tracking-wide
                     text-gray-500 dark:text-gray-400 select-none"
        >
          <span>Date</span>
          <span>Description</span>
          <span>Category</span>
          <span className="text-right">Amount</span>
          <span className="w-8" aria-hidden="true" />
        </div>

        {/* Transaction rows */}
        {visibleTransactions.map((tx) => {
          const amountClass =
            tx.type === "income"
              ? "text-green-600 dark:text-green-400"
              : "text-red-500 dark:text-red-400";

          const categoryName =
            tx.category_id === null ? "—" : categoryMap.get(tx.category_id) ?? "—";

          return (
            <div
              key={tx.id}
              role="row"
              onClick={() => onEdit(tx)}
              className="border-b last:border-b-0
                         border-gray-100 dark:border-gray-700
                         bg-white dark:bg-gray-800
                         hover:bg-gray-50 dark:hover:bg-gray-700/50
                         cursor-pointer transition-colors"
              aria-label={`Edit transaction: ${formatDate(tx.date)}, ${tx.description ?? "no description"}, ${categoryName}, ${formatCurrency(tx.amount)}`}
            >
              {/* Mobile layout (< sm): stacked two-line card */}
              <div className="flex items-center justify-between px-4 py-3 sm:hidden gap-3">
                <div className="flex flex-col min-w-0 gap-0.5">
                  <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {formatDate(tx.date)}
                  </span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                    {tx.description ?? categoryName}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-sm font-semibold ${amountClass}`}>
                    {formatCurrency(tx.amount)}
                  </span>
                  {/* Delete button */}
                  <button
                    type="button"
                    aria-label={`Delete transaction from ${formatDate(tx.date)}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteError(null);
                      setDeleteTarget(tx);
                    }}
                    className="flex items-center justify-center w-8 h-8 rounded-lg
                               text-gray-400 hover:text-red-500 dark:hover:text-red-400
                               hover:bg-red-50 dark:hover:bg-red-900/20
                               transition-colors focus:outline-none focus-visible:ring-2
                               focus-visible:ring-red-500"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Desktop layout (≥ sm): full grid row */}
              <div className="hidden sm:grid sm:grid-cols-[1fr_2fr_1fr_1fr_auto] gap-4 items-center px-4 py-3">
                {/* Date */}
                <span className="text-sm text-gray-700 dark:text-gray-200 whitespace-nowrap">
                  {formatDate(tx.date)}
                </span>

                {/* Description */}
                <span className="text-sm text-gray-600 dark:text-gray-300 truncate">
                  {tx.description ?? "—"}
                </span>

                {/* Category */}
                <span className="text-sm text-gray-600 dark:text-gray-300 truncate">
                  {categoryName}
                </span>

                {/* Amount */}
                <span className={`text-sm font-medium text-right ${amountClass}`}>
                  {formatCurrency(tx.amount)}
                </span>

                {/* Delete button (Req 10.1) */}
                <button
                  type="button"
                  aria-label={`Delete transaction from ${formatDate(tx.date)}`}
                  onClick={(e) => {
                    // Prevent the row's onEdit from firing
                    e.stopPropagation();
                    setDeleteError(null);
                    setDeleteTarget(tx);
                  }}
                  className="flex items-center justify-center w-8 h-8 rounded-lg
                             text-gray-400 hover:text-red-500 dark:hover:text-red-400
                             hover:bg-red-50 dark:hover:bg-red-900/20
                             transition-colors focus:outline-none focus-visible:ring-2
                             focus-visible:ring-red-500"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Paging footer */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500 dark:text-gray-400">
        <span>
          Showing {visibleTransactions.length} of {serverTotal} transactions
        </span>
        {visibleCount < transactions.length && (
          <button
            type="button"
            onClick={() => setVisibleCount((n) => n + LIST_PAGE_SIZE)}
            className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            Show more
          </button>
        )}
      </div>

      {/* Delete confirmation modal (Req 10.2–10.7) */}
      <ConfirmModal
        open={deleteTarget !== null}
        message={
          deleteTarget
            ? `Are you sure you want to delete this transaction? This action cannot be undone.`
            : ""
        }
        loading={deleting}
        error={deleteError}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          setDeleteTarget(null);
          setDeleteError(null);
        }}
      />
    </>
  );
}

export default TransactionList;
