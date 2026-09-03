import LoadingSpinner from "./LoadingSpinner";

interface ConfirmModalProps {
  /** Controls visibility of the modal */
  open: boolean;
  /** Question or warning text shown to the user */
  message: string;
  /** When true, the Confirm button is disabled and shows a spinner */
  loading: boolean;
  /** Inline error message to display inside the modal, or null if none */
  error: string | null;
  /** Called when the user clicks "Confirm" */
  onConfirm: () => void;
  /** Called when the user clicks "Cancel" */
  onCancel: () => void;
}

/**
 * Generic reusable confirmation dialog.
 *
 * - Disables the Confirm button and shows a LoadingSpinner while `loading` is true
 *   (Requirements 10.6).
 * - Displays an inline error message when `error` is non-null (Requirement 10.7).
 * - Closing via Cancel sends no API request (Requirement 10.3).
 */
export function ConfirmModal({
  open,
  message,
  loading,
  error,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  if (!open) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-message"
    >
      {/* Panel */}
      <div className="w-full max-w-sm rounded-2xl bg-white dark:bg-gray-800 shadow-xl p-6">
        {/* Message */}
        <p
          id="confirm-modal-message"
          className="text-sm text-gray-700 dark:text-gray-200 mb-6"
        >
          {message}
        </p>

        {/* Inline error */}
        {error && (
          <p
            role="alert"
            className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-3 py-2 text-xs text-red-600 dark:text-red-400"
          >
            {error}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors"
          >
            {loading && <LoadingSpinner size={4} />}
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmModal;
