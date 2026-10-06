import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import ConfirmModal from "../ui/ConfirmModal";
import LoadingSpinner from "../ui/LoadingSpinner";
import { formatRelativeTime } from "../../utils/formatters";
import type { Conversation } from "../../types";

/** Backend limit for a conversation title. */
const MAX_TITLE_LENGTH = 200;

const DELETE_WARNING = "Delete this conversation? All of its messages will be permanently removed.";

export const UNTITLED_CONVERSATION = "New conversation";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string | undefined;
  loading: boolean;
  error: string | null;
  actionError: string | null;
  includeArchived: boolean;
  hasMore: boolean;
  creating: boolean;
  onIncludeArchivedChange: (value: boolean) => void;
  onLoadMore: () => void;
  onNewChat: () => void;
  onRename: (id: string, title: string) => Promise<boolean>;
  onArchive: (id: string, archived: boolean) => Promise<boolean>;
  onDelete: (id: string) => Promise<boolean>;
  onClearActionError: () => void;
}

/**
 * Conversation list: New chat, inline rename, archive toggle, delete (with
 * confirmation) and a "show archived" filter. Selecting an item navigates to
 * /chat/<id>.
 */
export function ConversationSidebar({
  conversations,
  activeId,
  loading,
  error,
  actionError,
  includeArchived,
  hasMore,
  creating,
  onIncludeArchivedChange,
  onLoadMore,
  onNewChat,
  onRename,
  onArchive,
  onDelete,
  onClearActionError,
}: ConversationSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  // Enter commits and unmounts the input, which can fire onBlur too — commit once
  const editingRef = useRef<string | null>(null);

  function startRename(conv: Conversation) {
    onClearActionError();
    editingRef.current = conv.id;
    setEditingId(conv.id);
    setDraftTitle(conv.title ?? "");
  }

  async function commitRename(conv: Conversation) {
    if (editingRef.current !== conv.id) return;
    editingRef.current = null;
    const title = draftTitle.trim();
    setEditingId(null);
    // Empty or unchanged: nothing to send (the API can't clear a title anyway)
    if (!title || title === conv.title) return;
    await onRename(conv.id, title);
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    const ok = await onDelete(deleteTarget.id);
    setDeleteLoading(false);
    if (ok) setDeleteTarget(null);
  }

  return (
    <div className="flex h-full flex-col">
      {/* New chat */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={onNewChat}
          disabled={creating}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        >
          {creating ? <LoadingSpinner size={4} /> : <span aria-hidden="true">+</span>}
          New chat
        </button>
      </div>

      {/* Inline action error (rename / archive / create) */}
      {actionError && !deleteTarget && (
        <div
          role="alert"
          className="mx-3 mt-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-3 py-2 text-xs text-red-600 dark:text-red-400"
        >
          {actionError}
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {error ? (
          <p
            role="alert"
            className="m-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-3 py-2 text-xs text-red-600 dark:text-red-400"
          >
            {error}
          </p>
        ) : conversations.length === 0 && loading ? (
          <div className="flex justify-center py-8 text-gray-400">
            <LoadingSpinner size={6} />
          </div>
        ) : conversations.length === 0 ? (
          <p className="px-4 py-8 text-center text-xs text-gray-500 dark:text-gray-400">
            No conversations yet.
          </p>
        ) : (
          <ul className="p-2 space-y-1">
            {conversations.map((conv) => {
              const active = conv.id === activeId;
              const title = conv.title || UNTITLED_CONVERSATION;

              if (editingId === conv.id) {
                return (
                  <li key={conv.id} className="px-1 py-1">
                    <label htmlFor={`rename-${conv.id}`} className="sr-only">
                      Conversation title
                    </label>
                    <input
                      id={`rename-${conv.id}`}
                      autoFocus
                      value={draftTitle}
                      maxLength={MAX_TITLE_LENGTH}
                      onChange={(e) => setDraftTitle(e.target.value)}
                      onBlur={() => commitRename(conv)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          commitRename(conv);
                        } else if (e.key === "Escape") {
                          editingRef.current = null;
                          setEditingId(null);
                        }
                      }}
                      className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-2 py-1.5 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
                    />
                  </li>
                );
              }

              return (
                <li
                  key={conv.id}
                  className={`group flex items-center gap-1 rounded-lg transition-colors ${
                    active
                      ? "bg-indigo-50 dark:bg-indigo-900/30"
                      : "hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
                >
                  <Link
                    to={`/chat/${conv.id}`}
                    aria-current={active ? "page" : undefined}
                    className="min-w-0 flex-1 px-3 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-lg"
                  >
                    <span
                      className={`block truncate text-sm font-medium ${
                        active
                          ? "text-indigo-700 dark:text-indigo-300"
                          : "text-gray-800 dark:text-gray-100"
                      } ${conv.title ? "" : "italic"}`}
                    >
                      {title}
                    </span>
                    <span className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                      <time dateTime={conv.updated_at}>{formatRelativeTime(conv.updated_at)}</time>
                      {conv.archived && (
                        <span className="rounded-full bg-gray-100 dark:bg-gray-700 px-1.5 text-[10px] font-semibold text-gray-600 dark:text-gray-300">
                          Archived
                        </span>
                      )}
                    </span>
                  </Link>

                  {/* Row actions: always visible on touch, on hover/focus otherwise */}
                  <div className="flex shrink-0 items-center pr-1 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-opacity">
                    <IconButton label={`Rename ${title}`} onClick={() => startRename(conv)}>
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </IconButton>
                    <IconButton
                      label={conv.archived ? `Unarchive ${title}` : `Archive ${title}`}
                      onClick={() => {
                        onClearActionError();
                        onArchive(conv.id, !conv.archived);
                      }}
                    >
                      <rect x="2" y="3" width="20" height="5" rx="1" />
                      <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8" />
                      <path d="M10 12h4" />
                    </IconButton>
                    <IconButton
                      label={`Delete ${title}`}
                      danger
                      onClick={() => {
                        onClearActionError();
                        setDeleteTarget(conv);
                      }}
                    >
                      <path d="M3 6h18" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    </IconButton>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {hasMore && !error && (
          <div className="px-3 pb-3">
            <button
              type="button"
              onClick={onLoadMore}
              disabled={loading}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-60 transition-colors"
            >
              {loading ? "Loading…" : "Load more"}
            </button>
          </div>
        )}
      </div>

      {/* Show archived */}
      <label className="flex items-center gap-2 border-t border-gray-200 dark:border-gray-700 px-4 py-3 text-xs text-gray-600 dark:text-gray-400 cursor-pointer">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => onIncludeArchivedChange(e.target.checked)}
          className="rounded border-gray-300 dark:border-gray-600 text-indigo-600 focus:ring-indigo-500"
        />
        Show archived
      </label>

      <ConfirmModal
        open={!!deleteTarget}
        message={DELETE_WARNING}
        loading={deleteLoading}
        error={deleteTarget ? actionError : null}
        onConfirm={handleDeleteConfirm}
        onCancel={() => {
          setDeleteTarget(null);
          onClearActionError();
        }}
      />
    </div>
  );
}

interface IconButtonProps {
  label: string;
  danger?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function IconButton({ label, danger = false, onClick, children }: IconButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label.split(" ")[0]}
      className={`rounded-md p-1.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
        danger
          ? "text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-900/30"
          : "text-gray-400 hover:text-gray-700 hover:bg-gray-200 dark:hover:text-gray-200 dark:hover:bg-gray-700"
      }`}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {children}
      </svg>
    </button>
  );
}

export default ConversationSidebar;
