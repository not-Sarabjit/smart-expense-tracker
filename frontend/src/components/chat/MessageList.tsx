import { useEffect, useRef } from "react";
import EmptyState from "../ui/EmptyState";
import LoadingSpinner from "../ui/LoadingSpinner";
import MessageBubble from "./MessageBubble";
import type { ChatMessage } from "../../types";
import type { ChatError } from "../../hooks/useChat";

/** Within this many px of the bottom counts as "following" the conversation. */
const NEAR_BOTTOM_PX = 80;

interface MessageListProps {
  messages: ChatMessage[];
  loading: boolean;
  streaming: boolean;
  streamingText: string;
  error: ChatError | null;
  onRetry: () => void;
}

/**
 * Scrollable transcript. Auto-scrolls on new content only while the user is
 * already near the bottom, so reading scrollback isn't interrupted.
 * Mount with a `key` per conversation so a new transcript starts at the bottom.
 */
export function MessageList({
  messages,
  loading,
  streaming,
  streamingText,
  error,
  onRetry,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const nearBottom = useRef(true);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM_PX;
  }

  useEffect(() => {
    const el = scrollRef.current;
    if (el && nearBottom.current) el.scrollTop = el.scrollHeight;
  }, [messages, streaming, streamingText, error]);

  const visible = messages.filter(
    (m) => (m.role === "user" || m.role === "assistant") && m.content
  );
  const isEmpty = visible.length === 0 && !streaming && !streamingText;

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 sm:px-6 py-6"
      aria-live="polite"
      aria-busy={streaming}
    >
      {loading && visible.length === 0 ? (
        <div className="flex justify-center py-10">
          <LoadingSpinner size={8} />
        </div>
      ) : isEmpty && !error ? (
        <EmptyState message="No messages yet. Ask anything about your spending to get started." />
      ) : (
        <div className="mx-auto max-w-3xl space-y-4">
          {visible.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} />
          ))}

          {/* Live (or, after Stop, frozen) assistant reply */}
          {streamingText && (
            <MessageBubble
              role="assistant"
              content={streamingText}
              note={streaming ? undefined : "Stopped"}
            />
          )}

          {/* Typing indicator until the first token arrives */}
          {streaming && !streamingText && (
            <div className="flex justify-start" role="status" aria-label="Assistant is typing">
              <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3">
                <span className="h-2 w-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce [animation-delay:-0.3s]" />
                <span className="h-2 w-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce [animation-delay:-0.15s]" />
                <span className="h-2 w-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce" />
              </div>
            </div>
          )}

          {error && !streaming && (
            <div
              role="alert"
              className="rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-4 py-3 text-sm text-red-600 dark:text-red-400"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>{error.message}</span>
                <button
                  type="button"
                  onClick={onRetry}
                  className="rounded-lg border border-red-200 dark:border-red-700 px-3 py-1 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                >
                  Retry
                </button>
              </div>
              {error.requestId && (
                <p className="mt-1 text-[11px] text-red-400 dark:text-red-500/80 font-mono">
                  Request ID: {error.requestId}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MessageList;
