import { useState, useEffect, useCallback, useRef } from "react";
import {
  getAllMessages,
  streamChatMessage,
  getErrorStatus,
  ChatStreamError,
} from "../api/chat";
import { extractErrorMessage } from "../utils/errorHandling";
import type { ChatMessage } from "../types";

export interface ChatError {
  message: string;
  /** request_id from a stream `error` event, for support — shown in small print. */
  requestId: string | null;
}

interface UseChatOptions {
  /**
   * Called after each turn the server accepted (success or `error` event), so the
   * sidebar can bump the conversation; `title` is the new auto-title, if any.
   */
  onTurnComplete?: (conversationId: string, title: string | null) => void;
}

interface UseChatResult {
  /** Transcript, oldest first. Optimistic user messages carry a negative id. */
  messages: ChatMessage[];
  /** True while the transcript is being (re)loaded. */
  loading: boolean;
  streaming: boolean;
  /** Assistant text received so far; frozen (not cleared) right after stop(). */
  streamingText: string;
  /** Last send failure, or null. */
  error: ChatError | null;
  /** Transcript load failure, or null. */
  loadError: string | null;
  /** The conversation is missing, belongs to someone else, or the id is malformed. */
  notFound: boolean;
  /** A chat route answered 503 (AI_ENABLED is off). */
  disabled: boolean;
  send: (content: string) => Promise<void>;
  stop: () => void;
  retry: () => Promise<void>;
}

/**
 * Transcript + streaming state for one conversation.
 *
 * send() appends the user message optimistically, swaps in the server id from
 * `message_start`, accumulates `token` text into streamingText and appends the
 * finished assistant message on `message_end`. Any in-flight stream is aborted
 * on unmount or when `conversationId` changes.
 */
export function useChat(
  conversationId: string | undefined,
  options: UseChatOptions = {}
): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [streaming, setStreaming] = useState<boolean>(false);
  const [streamingText, setStreamingText] = useState<string>("");
  const [error, setError] = useState<ChatError | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState<boolean>(false);
  const [disabled, setDisabled] = useState<boolean>(false);

  const abortRef = useRef<AbortController | null>(null);
  const nextTempId = useRef(-1);
  const loadSeq = useRef(0);
  const messagesRef = useRef<ChatMessage[]>([]);
  messagesRef.current = messages;

  // Latest callback without re-creating send() on every parent render
  const onTurnCompleteRef = useRef(options.onTurnComplete);
  onTurnCompleteRef.current = options.onTurnComplete;

  const applyStatus = useCallback((err: unknown) => {
    const status = getErrorStatus(err);
    if (status === 503) setDisabled(true);
    // 422 here can only mean a malformed uuid in the path
    if (status === 404 || status === 422) setNotFound(true);
  }, []);

  /** Replaces the local transcript with what the server has. */
  const loadTranscript = useCallback(
    async (id: string) => {
      const seq = ++loadSeq.current;
      setLoading(true);
      setLoadError(null);
      try {
        const page = await getAllMessages(id);
        if (seq !== loadSeq.current) return;
        setMessages(page.items);
      } catch (err) {
        if (seq !== loadSeq.current) return;
        applyStatus(err);
        setLoadError(extractErrorMessage(err, "Failed to load messages."));
      } finally {
        if (seq === loadSeq.current) setLoading(false);
      }
    },
    [applyStatus]
  );

  // Reset and load whenever the conversation changes; abort any stream on leave
  useEffect(() => {
    setMessages([]);
    setStreaming(false);
    setStreamingText("");
    setError(null);
    setLoadError(null);
    setNotFound(false);
    setDisabled(false);

    if (conversationId) {
      loadTranscript(conversationId);
    } else {
      loadSeq.current++;
      setLoading(false);
    }

    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, [conversationId, loadTranscript]);

  const send = useCallback(
    async (raw: string) => {
      const content = raw.trim();
      if (!conversationId || !content || abortRef.current) return;

      const controller = new AbortController();
      abortRef.current = controller;
      const live = () => !controller.signal.aborted;

      const tempId = nextTempId.current--;
      setMessages((prev) => [
        ...prev,
        {
          id: tempId,
          conversation_id: conversationId,
          role: "user",
          content,
          tool_calls: null,
          meta: null,
          created_at: new Date().toISOString(),
        },
      ]);
      setError(null);
      setStreaming(true);
      setStreamingText("");

      let text = "";
      let started = false;

      try {
        await streamChatMessage(
          conversationId,
          content,
          {
            onStart: (ev) => {
              if (!live()) return;
              started = true;
              setMessages((prev) =>
                prev.map((m) => (m.id === tempId ? { ...m, id: ev.user_message_id } : m))
              );
            },
            onToken: (chunk) => {
              if (!live()) return;
              text += chunk;
              setStreamingText(text);
            },
            onEnd: (ev) => {
              if (!live()) return;
              setMessages((prev) => [
                ...prev,
                {
                  id: ev.message_id,
                  conversation_id: conversationId,
                  role: "assistant",
                  content: text || null,
                  tool_calls: null,
                  meta: { model: ev.model, usage: ev.usage, latency_ms: ev.latency_ms },
                  created_at: new Date().toISOString(),
                },
              ]);
              setStreamingText("");
              onTurnCompleteRef.current?.(conversationId, ev.title);
            },
            onError: (ev) => {
              if (!live()) return;
              // The user message is saved; the partial assistant text is not
              setStreamingText("");
              setError({
                message: ev.message || "The assistant could not finish this message.",
                requestId: ev.request_id || null,
              });
              onTurnCompleteRef.current?.(conversationId, null);
            },
          },
          controller.signal
        );
      } catch (err) {
        if (!live()) return;
        applyStatus(err);
        setStreamingText("");
        setError({
          message:
            err instanceof ChatStreamError
              ? err.message
              : extractErrorMessage(err, "Failed to send message."),
          requestId: null,
        });
        // The stream broke mid-turn: the server may hold more than we saw
        if (started) loadTranscript(conversationId);
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setStreaming(false);
        }
      }
    },
    [conversationId, applyStatus, loadTranscript]
  );

  const stop = useCallback(() => {
    const controller = abortRef.current;
    if (!controller || !conversationId) return;
    controller.abort();
    abortRef.current = null;
    setStreaming(false);
    // streamingText stays as-is (frozen) until the server's transcript arrives.
    // There is no cancellation endpoint yet, so the server's copy is the truth.
    loadTranscript(conversationId).finally(() => {
      if (!abortRef.current) setStreamingText("");
    });
  }, [conversationId, loadTranscript]);

  const retry = useCallback(async () => {
    if (abortRef.current) return;
    const lastUser = [...messagesRef.current].reverse().find((m) => m.role === "user");
    if (!lastUser?.content) return;
    // A negative id was never saved (pre-stream failure) — replace it, don't duplicate it
    if (lastUser.id < 0) {
      setMessages((prev) => prev.filter((m) => m.id !== lastUser.id));
    }
    await send(lastUser.content);
  }, [send]);

  return {
    messages,
    loading,
    streaming,
    streamingText,
    error,
    loadError,
    notFound,
    disabled,
    send,
    stop,
    retry,
  };
}
