import { useState, useCallback } from "react";
import type { Transaction } from "@/types";
import { useDashboardSummary } from "@/hooks/useDashboardSummary";
import { useTransactions } from "@/hooks/useTransactions";
import { useCategories } from "@/hooks/useCategories";
import MonthPicker from "@/components/dashboard/MonthPicker";
import SummaryCards from "@/components/dashboard/SummaryCards";
import BarChartWidget from "@/components/dashboard/BarChartWidget";
import DonutChartWidget from "@/components/dashboard/DonutChartWidget";
import TransactionList from "@/components/dashboard/TransactionList";
import TransactionForm from "@/components/transactions/TransactionForm";

/**
 * DashboardPage — the main authenticated view.
 *
 * Top-level state:
 *   - selectedYear / selectedMonth: default to current calendar year/month.
 *   - isAllTime: "All Time" toggle; defaults to false.
 *
 * Data fetching:
 *   - useDashboardSummary  → summary cards
 *   - useTransactions      → transaction list & charts
 *   - useCategories        → category name resolution & TransactionForm dropdown
 *
 * Mutations (create, edit, delete) call all three refetch functions on success.
 *
 * Requirements: 5.1–5.7, 6.1–6.8, 7.1–7.6, 8.1–8.8, 9.1–9.13, 10.1–10.7
 */
export default function DashboardPage() {
  // ── Calendar state ─────────────────────────────────────────────────────────
  const now = new Date();
  const [selectedYear, setSelectedYear] = useState<number>(now.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState<number>(now.getMonth() + 1); // 1–12
  const [isAllTime, setIsAllTime] = useState<boolean>(false);

  // ── Data hooks ─────────────────────────────────────────────────────────────
  const {
    summary,
    loading: summaryLoading,
    error: summaryError,
    refetch: summaryRefetch,
  } = useDashboardSummary({ year: selectedYear, month: selectedMonth, isAllTime });

  const {
    transactions,
    loading: txLoading,
    error: txError,
    refetch: transactionsRefetch,
  } = useTransactions({ year: selectedYear, month: selectedMonth, isAllTime });

  const {
    categories,
    refetch: categoriesRefetch,
  } = useCategories();

  // ── Month navigation ───────────────────────────────────────────────────────
  const handlePrevMonth = useCallback(() => {
    setSelectedMonth((m) => {
      if (m === 1) {
        setSelectedYear((y) => y - 1);
        return 12;
      }
      return m - 1;
    });
  }, []);

  const handleNextMonth = useCallback(() => {
    setSelectedMonth((m) => {
      if (m === 12) {
        setSelectedYear((y) => y + 1);
        return 1;
      }
      return m + 1;
    });
  }, []);

  const handleToggleAllTime = useCallback(() => {
    setIsAllTime((v) => !v);
  }, []);

  // ── Mutation success callback — calls all three refetches ──────────────────
  const handleMutationSuccess = useCallback(() => {
    summaryRefetch();
    transactionsRefetch();
    categoriesRefetch();
  }, [summaryRefetch, transactionsRefetch, categoriesRefetch]);

  // ── TransactionForm state ──────────────────────────────────────────────────
  const [formOpen, setFormOpen] = useState<boolean>(false);
  const [editTarget, setEditTarget] = useState<Transaction | null>(null);

  const openCreateForm = useCallback(() => {
    setEditTarget(null);
    setFormOpen(true);
  }, []);

  const openEditForm = useCallback((tx: Transaction) => {
    setEditTarget(tx);
    setFormOpen(true);
  }, []);

  const closeForm = useCallback(() => {
    setFormOpen(false);
    setEditTarget(null);
  }, []);

  const handleFormSuccess = useCallback(() => {
    handleMutationSuccess();
    closeForm();
  }, [handleMutationSuccess, closeForm]);

  // ── onDelete callback from TransactionList ─────────────────────────────────
  // TransactionList manages its own ConfirmModal internally; it calls onDelete
  // with the deleted transaction after a successful delete so the parent can refetch.
  const handleDeleteSuccess = useCallback((_tx: Transaction) => {
    handleMutationSuccess();
  }, [handleMutationSuccess]);

  // ── Derived chart data ─────────────────────────────────────────────────────
  const totalIncome = summary?.total_income ?? 0;
  const totalExpense = summary?.total_expense ?? 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* ── Month picker row ────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <MonthPicker
            year={selectedYear}
            month={selectedMonth}
            isAllTime={isAllTime}
            onPrev={handlePrevMonth}
            onNext={handleNextMonth}
            onToggleAllTime={handleToggleAllTime}
          />

          {/* Add Transaction FAB (Requirement 9.1) */}
          <button
            type="button"
            onClick={openCreateForm}
            className="flex items-center gap-2 rounded-full bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            aria-label="Add new transaction"
          >
            {/* Plus icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add Transaction
          </button>
        </div>

        {/* ── Summary cards (hidden when isAllTime) ───────────────────────── */}
        {!isAllTime && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <SummaryCards
              summary={summary}
              loading={summaryLoading}
              error={summaryError}
            />
          </div>
        )}

        {/* ── Charts row ──────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section aria-labelledby="bar-chart-heading" className="min-w-0">
            <h2
              id="bar-chart-heading"
              className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400"
            >
              Income vs Expenses
            </h2>
            <BarChartWidget
              totalIncome={totalIncome}
              totalExpense={totalExpense}
            />
          </section>

          <section aria-labelledby="donut-chart-heading" className="min-w-0">
            <h2
              id="donut-chart-heading"
              className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400"
            >
              Spending by Category
            </h2>
            <DonutChartWidget
              transactions={transactions}
              categories={categories}
            />
          </section>
        </div>

        {/* ── Transaction list ─────────────────────────────────────────────── */}
        <section aria-labelledby="transactions-heading">
          <h2
            id="transactions-heading"
            className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400"
          >
            Transactions
          </h2>
          <TransactionList
            transactions={transactions}
            categories={categories}
            loading={txLoading}
            error={txError}
            onEdit={openEditForm}
            onDelete={handleDeleteSuccess}
          />
        </section>
      </main>

      {/* ── TransactionForm modal ─────────────────────────────────────────── */}
      <TransactionForm
        open={formOpen}
        transaction={editTarget}
        categories={categories}
        onSuccess={handleFormSuccess}
        onClose={closeForm}
      />
    </div>
  );
}
