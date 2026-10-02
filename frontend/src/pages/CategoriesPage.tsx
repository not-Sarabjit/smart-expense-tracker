import { useState, useCallback } from "react";
import type { Category, CategoryType } from "../types";
import { useCategories } from "../hooks/useCategories";
import { createCategory, updateCategory, deleteCategory } from "../api/categories";
import { extractErrorMessage } from "../utils/errorHandling";
import ConfirmModal from "../components/ui/ConfirmModal";
import EmptyState from "../components/ui/EmptyState";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import axios from "axios";

// ─── Constants ────────────────────────────────────────────────────────────────

const DELETE_WARNING =
  "Delete this category? A category that is still used by transactions can't be deleted — move or delete those transactions first.";

const DUPLICATE_NAME_ERROR = "A category with this name already exists.";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Returns true if the Axios error is a 409 Conflict. */
function is409(err: unknown): boolean {
  return axios.isAxiosError(err) && err.response?.status === 409;
}

// ─── Create Form ──────────────────────────────────────────────────────────────

interface CreateFormState {
  name: string;
  category_type: CategoryType | "";
  nameError: string | null;
  submitting: boolean;
}

const INITIAL_CREATE: CreateFormState = {
  name: "",
  category_type: "",
  nameError: null,
  submitting: false,
};

// ─── Edit Modal ───────────────────────────────────────────────────────────────

interface EditFormState {
  name: string;
  category_type: CategoryType;
  nameError: string | null;
  submitting: boolean;
}

// ─── Page Component ───────────────────────────────────────────────────────────

/**
 * CategoriesPage — full CRUD management for income/expense categories.
 *
 * Requirements: 11.1–11.14
 */
export default function CategoriesPage() {
  const { categories, loading, error: fetchError, refetch } = useCategories();

  // Generic page-level error (non-409, non-fetch errors)
  const [pageError, setPageError] = useState<string | null>(null);

  // ── Create form state ────────────────────────────────────────────────────
  const [createForm, setCreateForm] = useState<CreateFormState>(INITIAL_CREATE);

  // ── Edit modal state ─────────────────────────────────────────────────────
  const [editTarget, setEditTarget] = useState<Category | null>(null);
  const [editForm, setEditForm] = useState<EditFormState>({
    name: "",
    category_type: "expense",
    nameError: null,
    submitting: false,
  });

  // ── Delete modal state ───────────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null);
  const [deleteLoading, setDeleteLoading] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // ── Create handlers ──────────────────────────────────────────────────────

  const handleCreateSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setPageError(null);
      setCreateForm((f) => ({ ...f, nameError: null }));

      // Client-side validation
      const trimmedName = createForm.name.trim();
      if (!trimmedName || !createForm.category_type) return;

      setCreateForm((f) => ({ ...f, submitting: true }));

      try {
        await createCategory({
          name: trimmedName,
          category_type: createForm.category_type as CategoryType,
        });
        setCreateForm(INITIAL_CREATE);
        refetch();
      } catch (err) {
        if (is409(err)) {
          setCreateForm((f) => ({
            ...f,
            submitting: false,
            nameError: DUPLICATE_NAME_ERROR,
          }));
        } else {
          setCreateForm((f) => ({ ...f, submitting: false }));
          setPageError(extractErrorMessage(err, "Failed to create category."));
        }
      }
    },
    [createForm.name, createForm.category_type, refetch]
  );

  // ── Edit handlers ────────────────────────────────────────────────────────

  const openEditModal = useCallback((cat: Category) => {
    setEditTarget(cat);
    setEditForm({
      name: cat.name,
      category_type: cat.category_type,
      nameError: null,
      submitting: false,
    });
    setPageError(null);
  }, []);

  const closeEditModal = useCallback(() => {
    setEditTarget(null);
  }, []);

  const handleEditSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!editTarget) return;

      setEditForm((f) => ({ ...f, nameError: null }));
      setPageError(null);

      const trimmedName = editForm.name.trim();
      if (!trimmedName) return;

      setEditForm((f) => ({ ...f, submitting: true }));

      try {
        await updateCategory(editTarget.id, {
          name: trimmedName,
          category_type: editForm.category_type,
        });
        setEditTarget(null);
        refetch();
      } catch (err) {
        if (is409(err)) {
          setEditForm((f) => ({
            ...f,
            submitting: false,
            nameError: DUPLICATE_NAME_ERROR,
          }));
        } else {
          setEditForm((f) => ({ ...f, submitting: false }));
          setPageError(extractErrorMessage(err, "Failed to update category."));
          setEditTarget(null);
        }
      }
    },
    [editTarget, editForm.name, editForm.category_type, refetch]
  );

  // ── Delete handlers ──────────────────────────────────────────────────────

  const openDeleteModal = useCallback((cat: Category) => {
    setDeleteTarget(cat);
    setDeleteError(null);
    setPageError(null);
  }, []);

  const closeDeleteModal = useCallback(() => {
    setDeleteTarget(null);
    setDeleteError(null);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;

    setDeleteLoading(true);
    setDeleteError(null);

    try {
      await deleteCategory(deleteTarget.id);
      setDeleteTarget(null);
      refetch();
    } catch (err) {
      setDeleteError(extractErrorMessage(err, "Failed to delete category."));
    } finally {
      setDeleteLoading(false);
    }
  }, [deleteTarget, refetch]);

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">

      <main className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Page heading */}
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Categories
        </h1>

        {/* ── Generic page-level error banner ─────────────────────────────── */}
        {pageError && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-4 py-3 text-sm text-red-600 dark:text-red-400"
          >
            {pageError}
          </div>
        )}

        {/* ── Create form ──────────────────────────────────────────────────── */}
        <section
          aria-labelledby="create-category-heading"
          className="rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 p-5"
        >
          <h2
            id="create-category-heading"
            className="text-base font-semibold text-gray-900 dark:text-white mb-4"
          >
            Create New Category
          </h2>

          <form
            onSubmit={handleCreateSubmit}
            noValidate
            className="flex flex-col sm:flex-row gap-3 items-start"
          >
            {/* Name input */}
            <div className="flex-1 min-w-0">
              <label
                htmlFor="create-name"
                className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1"
              >
                Name <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              <input
                id="create-name"
                type="text"
                value={createForm.name}
                maxLength={100}
                required
                placeholder="e.g. Groceries"
                onChange={(e) =>
                  setCreateForm((f) => ({
                    ...f,
                    name: e.target.value,
                    nameError: null,
                  }))
                }
                className={`w-full rounded-lg border px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 transition-colors ${
                  createForm.nameError
                    ? "border-red-400 dark:border-red-500"
                    : "border-gray-300 dark:border-gray-600"
                }`}
                aria-describedby={
                  createForm.nameError ? "create-name-error" : undefined
                }
                aria-invalid={!!createForm.nameError}
              />
              {/* 409 / name field error */}
              {createForm.nameError && (
                <p
                  id="create-name-error"
                  role="alert"
                  className="mt-1 text-xs text-red-500 dark:text-red-400"
                >
                  {createForm.nameError}
                </p>
              )}
            </div>

            {/* Type dropdown */}
            <div className="w-full sm:w-40">
              <label
                htmlFor="create-type"
                className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1"
              >
                Type <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              <select
                id="create-type"
                value={createForm.category_type}
                required
                onChange={(e) =>
                  setCreateForm((f) => ({
                    ...f,
                    category_type: e.target.value as CategoryType | "",
                  }))
                }
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 transition-colors"
              >
                <option value="" disabled>
                  Select type
                </option>
                <option value="income">Income</option>
                <option value="expense">Expense</option>
              </select>
            </div>

            {/* Submit */}
            <div className="sm:mt-5">
              <button
                type="submit"
                disabled={
                  createForm.submitting ||
                  !createForm.name.trim() ||
                  !createForm.category_type
                }
                className="flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              >
                {createForm.submitting && <LoadingSpinner size={4} />}
                Create
              </button>
            </div>
          </form>
        </section>

        {/* ── Category list ─────────────────────────────────────────────────── */}
        <section aria-labelledby="category-list-heading">
          <h2
            id="category-list-heading"
            className="text-base font-semibold text-gray-900 dark:text-white mb-3"
          >
            Your Categories
          </h2>

          {/* Fetch loading */}
          {loading && (
            <div className="flex justify-center py-10">
              <LoadingSpinner size={8} />
            </div>
          )}

          {/* Fetch error */}
          {!loading && fetchError && (
            <div
              role="alert"
              className="rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-4 py-3 text-sm text-red-600 dark:text-red-400"
            >
              {fetchError}
            </div>
          )}

          {/* Empty state (Requirement 11.14) */}
          {!loading && !fetchError && categories.length === 0 && (
            <EmptyState message="No categories yet. Create your first category above." />
          )}

          {/* List */}
          {!loading && !fetchError && categories.length > 0 && (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
              {categories.map((cat) => (
                <CategoryRow
                  key={cat.id}
                  category={cat}
                  onEdit={openEditModal}
                  onDelete={openDeleteModal}
                />
              ))}
            </ul>
          )}
        </section>
      </main>

      {/* ── Edit modal ────────────────────────────────────────────────────────── */}
      {editTarget && (
        <EditCategoryModal
          category={editTarget}
          form={editForm}
          setForm={setEditForm}
          onSubmit={handleEditSubmit}
          onCancel={closeEditModal}
        />
      )}

      {/* ── Delete confirm modal (Requirement 11.9) ──────────────────────────── */}
      <ConfirmModal
        open={!!deleteTarget}
        message={DELETE_WARNING}
        loading={deleteLoading}
        error={deleteError}
        onConfirm={handleDeleteConfirm}
        onCancel={closeDeleteModal}
      />
    </div>
  );
}

// ─── CategoryRow sub-component ────────────────────────────────────────────────

interface CategoryRowProps {
  category: Category;
  onEdit: (cat: Category) => void;
  onDelete: (cat: Category) => void;
}

function CategoryRow({ category, onEdit, onDelete }: CategoryRowProps) {
  return (
    <li className="flex items-center justify-between px-5 py-4 gap-3">
      {/* Name and type badge */}
      <div className="flex items-center gap-3 min-w-0">
        <span className="truncate text-sm font-medium text-gray-900 dark:text-white">
          {category.name}
        </span>

        {/* Type badge (Requirement 11.3) */}
        <span
          className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            category.category_type === "income"
              ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
              : "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400"
          }`}
        >
          {category.category_type === "income" ? "Income" : "Expense"}
        </span>

        {/* Built-in categories (user_id === null) are shared and read-only */}
        {category.user_id === null && (
          <span className="shrink-0 inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2.5 py-0.5 text-xs font-semibold text-gray-600 dark:text-gray-300">
            Default
          </span>
        )}
      </div>

      {/* Action buttons (custom categories only) */}
      {category.user_id !== null && (
      <div className="flex items-center gap-2 shrink-0">
        {/* Edit button */}
        <button
          type="button"
          onClick={() => onEdit(category)}
          className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          aria-label={`Edit category ${category.name}`}
        >
          Edit
        </button>

        {/* Delete button */}
        <button
          type="button"
          onClick={() => onDelete(category)}
          className="rounded-lg border border-red-200 dark:border-red-700 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          aria-label={`Delete category ${category.name}`}
        >
          Delete
        </button>
      </div>
      )}
    </li>
  );
}

// ─── EditCategoryModal sub-component ─────────────────────────────────────────

interface EditCategoryModalProps {
  category: Category;
  form: EditFormState;
  setForm: React.Dispatch<React.SetStateAction<EditFormState>>;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
}

function EditCategoryModal({
  category,
  form,
  setForm,
  onSubmit,
  onCancel,
}: EditCategoryModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-modal-heading"
    >
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800 shadow-xl p-6">
        {/* Heading */}
        <h2
          id="edit-modal-heading"
          className="text-base font-semibold text-gray-900 dark:text-white mb-5"
        >
          Edit Category
        </h2>

        <form onSubmit={onSubmit} noValidate className="space-y-4">
          {/* Name field */}
          <div>
            <label
              htmlFor="edit-name"
              className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1"
            >
              Name <span aria-hidden="true" className="text-red-500">*</span>
            </label>
            <input
              id="edit-name"
              type="text"
              value={form.name}
              maxLength={100}
              required
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  name: e.target.value,
                  nameError: null,
                }))
              }
              className={`w-full rounded-lg border px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 transition-colors ${
                form.nameError
                  ? "border-red-400 dark:border-red-500"
                  : "border-gray-300 dark:border-gray-600"
              }`}
              aria-describedby={form.nameError ? "edit-name-error" : undefined}
              aria-invalid={!!form.nameError}
            />
            {/* 409 / name field error */}
            {form.nameError && (
              <p
                id="edit-name-error"
                role="alert"
                className="mt-1 text-xs text-red-500 dark:text-red-400"
              >
                {form.nameError}
              </p>
            )}
          </div>

          {/* Type dropdown */}
          <div>
            <label
              htmlFor="edit-type"
              className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1"
            >
              Type <span aria-hidden="true" className="text-red-500">*</span>
            </label>
            <select
              id="edit-type"
              value={form.category_type}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  category_type: e.target.value as CategoryType,
                }))
              }
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 transition-colors"
            >
              <option value="income">Income</option>
              <option value="expense">Expense</option>
            </select>
          </div>

          {/* Hidden category id for accessibility context */}
          <p className="sr-only">Editing: {category.name}</p>

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onCancel}
              disabled={form.submitting}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={form.submitting || !form.name.trim()}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              {form.submitting && <LoadingSpinner size={4} />}
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
