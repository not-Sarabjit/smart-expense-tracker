import { useCallback, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useConversations } from "../hooks/useConversations";
import { useChat } from "../hooks/useChat";
import ChatPanel from "../components/chat/ChatPanel";
import ConversationSidebar, {
  UNTITLED_CONVERSATION,
} from "../components/chat/ConversationSidebar";
import MessageList from "../components/chat/MessageList";
import ChatComposer from "../components/chat/ChatComposer";
import EmptyState from "../components/ui/EmptyState";

/**
 * ChatPage — the AI assistant. Routes: /chat and /chat/:conversationId.
 *
 * - No id: sidebar plus an empty state; creating or picking a conversation
 *   navigates to /chat/<uuid>.
 * - Unknown / foreign / malformed id: "Conversation not found".
 * - Any 503 from a chat route: a single "assistant is turned off" panel.
 */
export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const navigate = useNavigate();

  const convs = useConversations();
  const { touch } = convs;
  const [creating, setCreating] = useState(false);

  const handleTurnComplete = useCallback(
    (id: string, title: string | null) => touch(id, { title }),
    [touch]
  );
  const chat = useChat(conversationId, { onTurnComplete: handleTurnComplete });

  const handleNewChat = useCallback(async () => {
    setCreating(true);
    const conv = await convs.create();
    setCreating(false);
    if (conv) navigate(`/chat/${conv.id}`);
  }, [convs, navigate]);

  const handleDelete = useCallback(
    async (id: string) => {
      const ok = await convs.remove(id);
      if (ok && id === conversationId) navigate("/chat");
      return ok;
    },
    [convs, conversationId, navigate]
  );

  // ── AI disabled: one clear panel, no retries ──────────────────────────────
  if (convs.disabled || chat.disabled) {
    return (
      <div className="min-h-[calc(100dvh-4rem)] bg-gray-50 dark:bg-gray-900">
        <main className="mx-auto max-w-xl px-4 py-16">
          <div
            role="status"
            className="rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center"
          >
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
              The AI assistant is currently turned off
            </h1>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Chat isn't available right now. The rest of the app works as usual.
            </p>
            <Link
              to="/dashboard"
              className="mt-6 inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition-colors"
            >
              Back to dashboard
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const active = convs.conversations.find((c) => c.id === conversationId);
  const headerTitle = !conversationId
    ? "Chat"
    : chat.notFound
      ? "Not found"
      : active
        ? active.title || UNTITLED_CONVERSATION
        : "";

  const sidebar = (
    <ConversationSidebar
      conversations={convs.conversations}
      activeId={conversationId}
      loading={convs.loading}
      error={convs.error}
      actionError={convs.actionError}
      includeArchived={convs.includeArchived}
      hasMore={convs.hasMore}
      creating={creating}
      onIncludeArchivedChange={convs.setIncludeArchived}
      onLoadMore={convs.loadMore}
      onNewChat={handleNewChat}
      onRename={convs.rename}
      onArchive={convs.setArchived}
      onDelete={handleDelete}
      onClearActionError={convs.clearActionError}
    />
  );

  let body;
  if (!conversationId) {
    body = (
      <div className="flex flex-1 items-center justify-center">
        <div>
          <EmptyState message="Pick a conversation, or start a new one to ask about your spending." />
          <div className="flex justify-center">
            <button
              type="button"
              onClick={handleNewChat}
              disabled={creating}
              className="rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              New chat
            </button>
          </div>
        </div>
      </div>
    );
  } else if (chat.notFound) {
    body = (
      <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          Conversation not found
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          It may have been deleted, or the link is wrong.
        </p>
        <Link
          to="/chat"
          className="mt-4 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          Back to chat
        </Link>
      </div>
    );
  } else {
    body = (
      <>
        {chat.loadError && (
          <div
            role="alert"
            className="mx-4 sm:mx-6 mt-4 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-4 py-3 text-sm text-red-600 dark:text-red-400"
          >
            {chat.loadError}
          </div>
        )}
        <MessageList
          key={conversationId}
          messages={chat.messages}
          loading={chat.loading}
          streaming={chat.streaming}
          streamingText={chat.streamingText}
          error={chat.error}
          onRetry={chat.retry}
        />
        <ChatComposer
          key={`composer-${conversationId}`}
          streaming={chat.streaming}
          disabled={chat.loading && chat.messages.length === 0}
          onSend={chat.send}
          onStop={chat.stop}
        />
      </>
    );
  }

  return (
    <ChatPanel sidebar={sidebar} title={headerTitle}>
      {body}
    </ChatPanel>
  );
}
