import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Transaction, Category, TransactionType } from "@/types";
import { createTransaction, updateTransaction, deleteTransaction } from "@/api/transactions";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ConfirmModal } from "@/components/ui/ConfirmModal";

export interface TransactionFormProps {
  open: boolean;
  transaction: Transaction | null; // null = create mode
  categories: Category[];
  onSuccess: () => void;
  onClose: () => void;
}

interface FieldErrors {
  amount?: string;
  date?: string;
  type?: string;
  category_id?: string;
  description?: string;
}

/** Returns today's date as "YYYY-MM-DD" in local time */
function getTodayString(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Modal form for creating and editing transactions.
 *
 * - Create mode (transaction === null): empty fields, date defaults to today.
 * - Edit mode (transaction !== null): pre-populated fields, shows Delete button.
 * - On type change: filters categories by type and clears category selection.
 * - Sends POST /transactions (create) or PUT /transactions/{id} (edit).
 * - Handles 422 field-level errors and generic errors separately.
 * - Disables submit and shows LoadingSpinner while in-flight.
 * - Delete button (edit mode) opens ConfirmModal; on 204 closes both and refetches.
 *
 * Requirements: 9.1–9.13, 10.1–10.7
 */
export function TransactionForm({
  open,
  transaction,
  categories,
  onSuccess,
  onClose,
}: TransactionFormProps) {
  const isEditMode = transaction !== null;
  const today = getTodayString();

  // ── Form state ─────────────────────────────────────────────────────────────
  const [amount, setAmount] = useState<string>("");
  const [date, setDate] = useState<string>(today);
  const [type, setType] = useState<TransactionType>("expense");
  const [categoryId, setCategoryId] = useState<string>("");
  const [description, setDescription] = useState<string>("");

  // ── Error state ────────────────────────────────────────────────────────────
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [globalError, setGlobalError] = useState<string | null>(null);

  // ── Submission state ───────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false);

  // ── Delete confirmation state ──────────────────────────────────────────────
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // ── Filtered categories ────────────────────────────────────────────────────
  const filteredCategories = categories.filter((c) => c.category_type === type);

  // ── Populate fields when the form opens ───────────────────────────────────
  useEffect(() => {
    if (!open) return;

    // Clear all errors when modal opens
    setFieldErrors({});
    setGlobalError(null);
    setConfirmDeleteOpen(false);
    setDeleteError(null);

    if (isEditMode && transaction) {
      setAmount(String(transaction.amount));
      setDate(transaction.date);
      setType(transaction.type);
      setCategoryId(String(transaction.category_id));
      setDescription(transaction.description ?? "");
    } else {
      // Create mode — reset to defaults
      setAmount("");
      setDate(today);
      setType("expense");
      setCategoryId("");
      setDescription("");
    }
  }, [open, transaction, isEditMode, today]);

  // ── When type changes, filter categories and clear selection ───────────────
  const handleTypeChange = useCallback((newType: TransactionType) => {
    setType(newType);
    setCategoryId("");
    setFieldErrors((prev) => ({ ...prev, category_id: undefined, type: undefined }));
  }, []);

  // ── Map FastAPI 422 detail array to field-level errors ────────────────────
  function extract422FieldErrors(err: unknown): FieldErrors | null {
    if (!axios.isAxiosError(err)) return null;
    if (err.response?.status !== 422) return null;

    const detail = err.response?.data?.detail;
    if (!Array.isArray(detail)) return null;

    const validFields = new Set(["amount", "date", "type", "category_id", "description"]);
    const errors: FieldErrors = {};
    for (const item of detail) {
      const loc: string[] = item.loc ?? [];
      const fieldName = loc[loc.length - 1];
      if (fieldName && validFields.has(fieldName)) {
        errors[fieldName as keyof FieldErrors] = item.msg;
      }
    }
    return errors;
  }

  // ── Client-side validation ─────────────────────────────────────────────────
  function validateForm(): FieldErrors {
    const errors: FieldErrors = {};
    const amountNum = parseFloat(amount);

    if (!amount || isNaN(amountNum)) {
      errors.amount = "Amount is required.";
    } else if (amountNum < 0.01 || amountNum > 9_999_999_999.99) {
      errors.amount = "Amount must be between 0.01 and 9,999,999,999.99.";
    }

    if (!date) {
      errors.date = "Date is required.";
    } else if (date > today) {
      errors.date = "Date cannot be in the future.";
    }

    if (!type) {
      errors.type = "Type is required.";
    }

    if (!categoryId) {
      errors.category_id = "Category is required.";
    }

    if (description.length > 255) {
      errors.description = "Description must be 255 characters or fewer.";
    }

    return errors;
  }

  // ── Form submission ────────────────────────────────────────────────────────
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const clientErrors = validateForm();
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setFieldErrors({});
    setGlobalError(null);
    setSubmitting(true);

    const payload = {
      amount: parseFloat(amount),
      date,
      type,
      category_id: parseInt(categoryId, 10),
      description: description.trim() || null,
    };

    try {
      if (isEditMode && transaction) {
        // Build partial payload (only changed fields)
        const updatePayload: Partial<typeof payload> = {};
        if (payload.amount !== transaction.amount) updatePayload.amount = payload.amount;
        if (payload.date !== transaction.date) updatePayload.date = payload.date;
        if (payload.type !== transaction.type) updatePayload.type = payload.type;
        if (payload.category_id !== transaction.category_id) updatePayload.category_id = payload.category_id;
        if (payload.description !== transaction.description) updatePayload.description = payload.description;

        await updateTransaction(transaction.id, updatePayload);
      } else {
        await createTransaction(payload);
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      // Try 422 field-level errors first
      const fieldErrs = extract422FieldErrors(err);
      if (fieldErrs && Object.keys(fieldErrs).length > 0) {
        setFieldErrors(fieldErrs);
      } else if (axios.isAxiosError(err) && err.response?.status === 422) {
        setGlobalError("Validation failed. Please check your inputs.");
      } else {
        // Non-422 error
        if (axios.isAxiosError(err)) {
          const detail = err.response?.data?.detail;
          if (typeof detail === "string") {
            setGlobalError(detail);
          } else if (Array.isArray(detail)) {
            setGlobalError(detail.map((d) => d.msg).join(", "));
          } else if (!err.response) {
            setGlobalError("Unable to reach server. Please check your connection.");
          } else {
            setGlobalError("An unexpected error occurred. Please try again.");
          }
        } else {
          setGlobalError("An unexpected error occurred. Please try again.");
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  // ── Delete handler ─────────────────────────────────────────────────────────
  async function handleConfirmDelete() {
    if (!transaction) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteTransaction(transaction.id);
      // On 204: close confirm modal and form, then trigger refetch
      setConfirmDeleteOpen(false);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      // Display inline error in ConfirmModal without closing it (Req 10.7)
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === "string") {
          setDeleteError(detail);
        } else if (Array.isArray(detail)) {
          setDeleteError(detail.map((d) => d.msg).join(", "));
        } else if (!err.response) {
          setDeleteError("Unable to reach server. Please check your connection.");
        } else {
          setDeleteError("Failed to delete transaction. Please try again.");
        }
      } else {
        setDeleteError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setDeleting(false);
    }
  }

  // ── Computed helpers ───────────────────────────────────────────────────────
  const hasNoMatchingCategories = filteredCategories.length === 0;
  const isSubmitDisabled = submitting || hasNoMatchingCategories;

  if (!open) return null;

  return (
    <>
      {/* Backdrop / modal panel */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="transaction-form-title"
      >
        {/* Panel */}
        <div className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800 shadow-xl overflow-y-auto max-h-[90vh]">
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100 dark:border-gray-700">
            <h2
              id="transaction-form-title"
              className="text-base font-semibold text-gray-900 dark:text-gray-100"
            >
              {isEditMode ? "Edit Transaction" : "Add Transaction"}
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close form"
              className="rounded-lg p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} noValidate className="px-6 py-5 space-y-4">
            {/* Global error banner */}
            {globalError && (
              <div
                role="alert"
                className="rounded-lg border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/30 px-3 py-2 text-sm text-red-600 dark:text-red-400"
              >
                {globalError}
              </div>
            )}

            {/* Amount */}
            <div>
              <label
                htmlFor="tx-amount"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Amount <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              <input
                id="tx-amount"
                type="number"
                step="0.01"
                min="0.01"
                max="9999999999.99"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value);
                  setFieldErrors((prev) => ({ ...prev, amount: undefined }));
                }}
                placeholder="0.00"
                required
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors"
                aria-describedby={fieldErrors.amount ? "tx-amount-error" : undefined}
                aria-invalid={!!fieldErrors.amount}
              />
              {fieldErrors.amount && (
                <p id="tx-amount-error" role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
                  {fieldErrors.amount}
                </p>
              )}
            </div>

            {/* Date */}
            <div>
              <label
                htmlFor="tx-date"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Date <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              <input
                id="tx-date"
                type="date"
                max={today}
                value={date}
                onChange={(e) => {
                  setDate(e.target.value);
                  setFieldErrors((prev) => ({ ...prev, date: undefined }));
                }}
                required
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors"
                aria-describedby={fieldErrors.date ? "tx-date-error" : undefined}
                aria-invalid={!!fieldErrors.date}
              />
              {fieldErrors.date && (
                <p id="tx-date-error" role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
                  {fieldErrors.date}
                </p>
              )}
            </div>

            {/* Type */}
            <div>
              <label
                htmlFor="tx-type"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Type <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              <select
                id="tx-type"
                value={type}
                onChange={(e) => handleTypeChange(e.target.value as TransactionType)}
                required
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors"
                aria-describedby={fieldErrors.type ? "tx-type-error" : undefined}
                aria-invalid={!!fieldErrors.type}
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
              {fieldErrors.type && (
                <p id="tx-type-error" role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
                  {fieldErrors.type}
                </p>
              )}
            </div>

            {/* Category */}
            <div>
              <label
                htmlFor="tx-category"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Category <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              {hasNoMatchingCategories ? (
                <p
                  className="rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 px-3 py-2 text-sm text-gray-500 dark:text-gray-400"
                >
                  No {type} categories available. Please create one first.
                </p>
              ) : (
                <select
                  id="tx-category"
                  value={categoryId}
                  onChange={(e) => {
                    setCategoryId(e.target.value);
                    setFieldErrors((prev) => ({ ...prev, category_id: undefined }));
                  }}
                  required
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors"
                  aria-describedby={fieldErrors.category_id ? "tx-category-error" : undefined}
                  aria-invalid={!!fieldErrors.category_id}
                >
                  <option value="">Select a category</option>
                  {filteredCategories.map((cat) => (
                    <option key={cat.id} value={String(cat.id)}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              )}
              {fieldErrors.category_id && (
                <p id="tx-category-error" role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
                  {fieldErrors.category_id}
                </p>
              )}
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="tx-description"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Description{" "}
                <span className="text-gray-400 dark:text-gray-500 font-normal">(optional)</span>
              </label>
              <input
                id="tx-description"
                type="text"
                maxLength={255}
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  setFieldErrors((prev) => ({ ...prev, description: undefined }));
                }}
                placeholder="Add a note…"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors"
                aria-describedby={fieldErrors.description ? "tx-description-error" : undefined}
                aria-invalid={!!fieldErrors.description}
              />
              <div className="flex items-center justify-between mt-1">
                {fieldErrors.description ? (
                  <p id="tx-description-error" role="alert" className="text-xs text-red-600 dark:text-red-400">
                    {fieldErrors.description}
                  </p>
                ) : (
                  <span />
                )}
                <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums">
                  {description.length}/255
                </span>
              </div>
            </div>

            {/* Footer: Delete (edit mode) + Cancel + Submit */}
            <div className="flex items-center justify-between pt-2 gap-3">
              {/* Delete button — only in edit mode (Req 10.1) */}
              {isEditMode ? (
                <button
                  type="button"
                  onClick={() => {
                    setDeleteError(null);
                    setConfirmDeleteOpen(true);
                  }}
                  disabled={submitting}
                  className="rounded-lg border border-red-300 dark:border-red-700 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Delete
                </button>
              ) : (
                /* Spacer to keep Cancel/Submit right-aligned */
                <span aria-hidden="true" />
              )}

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={submitting}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={isSubmitDisabled}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors"
                >
                  {submitting && <LoadingSpinner size={4} />}
                  {isEditMode ? "Save Changes" : "Add Transaction"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Delete confirmation modal (Req 10.2–10.7) */}
      <ConfirmModal
        open={confirmDeleteOpen}
        message="Are you sure you want to delete this transaction? This action cannot be undone."
        loading={deleting}
        error={deleteError}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          setConfirmDeleteOpen(false);
          setDeleteError(null);
        }}
      />
    </>
  );
}

export default TransactionForm;
