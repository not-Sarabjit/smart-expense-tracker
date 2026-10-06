import { useState, useEffect, useCallback, useRef } from "react";
import {
  getConversations,
  createConversation,
  updateConversation,
  deleteConversation,
  getErrorStatus,
} from "../api/chat";
import { extractErrorMessage } from "../utils/errorHandling";
import type { Conversation } from "../types";

/** Sidebar page size (the API default). */
const PAGE_SIZE = 50;

interface UseConversationsResult {
  /** Sorted updated_at DESC, id DESC — the same order the API uses. */
  conversations: Conversation[];
  /** Total matching rows on the server (X-Total-Count). */
  total: number;
  loading: boolean;
  /** Load error for the list, or null. */
  error: string | null;
  /** Error from the last create/rename/archive/delete, or null. */
  actionError: string | null;
  /** True once any chat route has answered 503 (AI_ENABLED is off). */
  disabled: boolean;
  includeArchived: boolean;
  setIncludeArchived: (value: boolean) => void;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
  clearActionError: () => void;
  create: (title?: string) => Promise<Conversation | null>;
  rename: (id: string, title: string) => Promise<boolean>;
  setArchived: (id: string, archived: boolean) => Promise<boolean>;
  remove: (id: string) => Promise<boolean>;
  /** Local-only update after a chat turn: bumps updated_at and applies a new auto-title. */
  touch: (id: string, changes?: { title?: string | null }) => void;
}

function sortConversations(list: Conversation[]): Conversation[] {
  return [...list].sort((a, b) => {
    const diff = Date.parse(b.updated_at) - Date.parse(a.updated_at);
    if (diff !== 0) return diff;
    return a.id < b.id ? 1 : a.id > b.id ? -1 : 0;
  });
}

/** Replaces (or inserts) one conversation and re-sorts. */
function upsert(list: Conversation[], conv: Conversation): Conversation[] {
  return sortConversations([...list.filter((c) => c.id !== conv.id), conv]);
}

/**
 * Loads the user's chat conversations for the sidebar and wraps the
 * create / rename / archive / delete calls, keeping the local list in the
 * server's order without a full re-fetch after every change.
 */
export function useConversations(): UseConversationsResult {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [disabled, setDisabled] = useState<boolean>(false);
  const [includeArchived, setIncludeArchived] = useState<boolean>(false);

  // Ignore responses from a superseded load (e.g. archived toggle clicked twice)
  const requestSeq = useRef(0);

  const handleFailure = useCallback((err: unknown, fallback: string): string => {
    if (getErrorStatus(err) === 503) setDisabled(true);
    return extractErrorMessage(err, fallback);
  }, []);

  const refresh = useCallback(async () => {
    const seq = ++requestSeq.current;
    setLoading(true);
    setError(null);
    try {
      const page = await getConversations({
        include_archived: includeArchived,
        limit: PAGE_SIZE,
        offset: 0,
      });
      if (seq !== requestSeq.current) return;
      setConversations(sortConversations(page.items));
      setTotal(page.total);
    } catch (err) {
      if (seq !== requestSeq.current) return;
      setError(handleFailure(err, "Failed to load conversations."));
      setConversations([]);
      setTotal(0);
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  }, [includeArchived, handleFailure]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const loadMore = useCallback(async () => {
    const seq = requestSeq.current;
    setLoading(true);
    try {
      const page = await getConversations({
        include_archived: includeArchived,
        limit: PAGE_SIZE,
        offset: conversations.length,
      });
      if (seq !== requestSeq.current) return;
      setConversations((prev) => {
        const seen = new Set(prev.map((c) => c.id));
        return sortConversations([...prev, ...page.items.filter((c) => !seen.has(c.id))]);
      });
      setTotal(page.total);
    } catch (err) {
      if (seq !== requestSeq.current) return;
      setError(handleFailure(err, "Failed to load more conversations."));
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  }, [includeArchived, conversations.length, handleFailure]);

  const create = useCallback(
    async (title?: string) => {
      setActionError(null);
      try {
        const conv = await createConversation(title ? { title } : undefined);
        setConversations((prev) => upsert(prev, conv));
        setTotal((t) => t + 1);
        return conv;
      } catch (err) {
        setActionError(handleFailure(err, "Failed to create conversation."));
        return null;
      }
    },
    [handleFailure]
  );

  const rename = useCallback(
    async (id: string, title: string) => {
      setActionError(null);
      try {
        const conv = await updateConversation(id, { title });
        setConversations((prev) => upsert(prev, conv));
        return true;
      } catch (err) {
        setActionError(handleFailure(err, "Failed to rename conversation."));
        return false;
      }
    },
    [handleFailure]
  );

  const setArchived = useCallback(
    async (id: string, archived: boolean) => {
      setActionError(null);
      try {
        const conv = await updateConversation(id, { archived });
        if (archived && !includeArchived) {
          // No longer part of the visible list
          setConversations((prev) => prev.filter((c) => c.id !== id));
          setTotal((t) => Math.max(0, t - 1));
        } else {
          setConversations((prev) => upsert(prev, conv));
        }
        return true;
      } catch (err) {
        setActionError(
          handleFailure(err, archived ? "Failed to archive conversation." : "Failed to unarchive conversation.")
        );
        return false;
      }
    },
    [includeArchived, handleFailure]
  );

  const remove = useCallback(
    async (id: string) => {
      setActionError(null);
      try {
        await deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        setTotal((t) => Math.max(0, t - 1));
        return true;
      } catch (err) {
        setActionError(handleFailure(err, "Failed to delete conversation."));
        return false;
      }
    },
    [handleFailure]
  );

  const touch = useCallback((id: string, changes?: { title?: string | null }) => {
    setConversations((prev) => {
      const current = prev.find((c) => c.id === id);
      if (!current) return prev;
      return upsert(prev, {
        ...current,
        title: changes?.title ?? current.title,
        updated_at: new Date().toISOString(),
      });
    });
  }, []);

  const clearActionError = useCallback(() => setActionError(null), []);

  return {
    conversations,
    total,
    loading,
    error,
    actionError,
    disabled,
    includeArchived,
    setIncludeArchived,
    hasMore: conversations.length < total,
    loadMore,
    refresh,
    clearActionError,
    create,
    rename,
    setArchived,
    remove,
    touch,
  };
}
