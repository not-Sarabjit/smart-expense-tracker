import axios from "axios";
import apiClient from "./client";
import { createSSEParser } from "./sse";
import { NETWORK_ERROR_MESSAGE } from "../utils/errorHandling";
import type {
  Conversation,
  ConversationPage,
  ConversationCreatePayload,
  ConversationUpdatePayload,
  ChatMessage,
  ChatMessagePage,
  MessageStartEvent,
  MessageEndEvent,
  StreamErrorEvent,
} from "../types";

/** Largest page the chat list endpoints accept (`limit` ≤ 200). */
export const MAX_CHAT_PAGE_SIZE = 200;

/** Message length bounds enforced by the backend (after trimming). */
export const MAX_MESSAGE_LENGTH = 4000;

export interface GetConversationsParams {
  include_archived?: boolean;
  limit?: number;
  offset?: number;
}

export interface GetMessagesParams {
  limit?: number;
  offset?: number;
}

/** Reads X-Total-Count, falling back to the page length when it is missing or bogus. */
function readTotal(headers: unknown, fallback: number): number {
  const header = (headers as Record<string, unknown> | undefined)?.["x-total-count"];
  const total = header !== undefined ? Number(header) : fallback;
  return Number.isFinite(total) ? total : fallback;
}

// ─── REST ─────────────────────────────────────────────────────────────────────

/** Fetches one page of conversations (updated_at DESC) plus the total (X-Total-Count). */
export function getConversations(
  params?: GetConversationsParams
): Promise<ConversationPage> {
  return apiClient
    .get<Conversation[]>("/chat/conversations", { params })
    .then((res) => ({ items: res.data, total: readTotal(res.headers, res.data.length) }));
}

export function getConversation(id: string): Promise<Conversation> {
  return apiClient
    .get<Conversation>(`/chat/conversations/${id}`)
    .then((res) => res.data);
}

export function createConversation(
  payload?: ConversationCreatePayload
): Promise<Conversation> {
  return apiClient
    .post<Conversation>("/chat/conversations", payload ?? {})
    .then((res) => res.data);
}

/** Only the fields present in `payload` are applied by the server. */
export function updateConversation(
  id: string,
  payload: ConversationUpdatePayload
): Promise<Conversation> {
  return apiClient
    .patch<Conversation>(`/chat/conversations/${id}`, payload)
    .then((res) => res.data);
}

export function deleteConversation(id: string): Promise<void> {
  return apiClient.delete(`/chat/conversations/${id}`).then(() => undefined);
}

/** Fetches one page of a transcript (oldest first) plus the total (X-Total-Count). */
export function getMessages(
  conversationId: string,
  params?: GetMessagesParams
): Promise<ChatMessagePage> {
  return apiClient
    .get<ChatMessage[]>(`/chat/conversations/${conversationId}/messages`, { params })
    .then((res) => ({ items: res.data, total: readTotal(res.headers, res.data.length) }));
}

/** Fetches the whole transcript, paging with the largest allowed page size. */
export async function getAllMessages(conversationId: string): Promise<ChatMessagePage> {
  const items: ChatMessage[] = [];
  let total = 0;
  do {
    const page = await getMessages(conversationId, {
      limit: MAX_CHAT_PAGE_SIZE,
      offset: items.length,
    });
    items.push(...page.items);
    total = page.total;
    if (page.items.length === 0) break;
  } while (items.length < total);

  return { items, total };
}

// ─── Streaming send ───────────────────────────────────────────────────────────

/**
 * A send that failed before or during the stream.
 * `status` is the HTTP status for pre-stream failures, 0 for network/stream loss.
 */
export class ChatStreamError extends Error {
  status: number;
  /** Seconds to wait, from Retry-After on a 429; null otherwise. */
  retryAfter: number | null;

  constructor(status: number, message: string, retryAfter: number | null = null) {
    super(message);
    this.name = "ChatStreamError";
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

/** HTTP status of a failed chat call (axios or streaming), or null if there was none. */
export function getErrorStatus(err: unknown): number | null {
  if (err instanceof ChatStreamError) return err.status || null;
  if (axios.isAxiosError(err)) return err.response?.status ?? null;
  return null;
}

/** Same message precedence as extractErrorMessage: `message`, then `detail`. */
function messageFromBody(body: unknown, fallback: string): string {
  const data = body as { message?: unknown; detail?: unknown } | null;
  if (typeof data?.message === "string") return data.message;
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) {
    return data.detail.map((d: { msg?: string }) => d.msg).join(", ");
  }
  return fallback;
}

async function errorFromResponse(response: Response): Promise<ChatStreamError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // non-JSON error body (e.g. proxy error page) — use the fallback message
  }
  let message = messageFromBody(body, `Request failed (${response.status}).`);

  let retryAfter: number | null = null;
  if (response.status === 429) {
    const seconds = Number(response.headers.get("Retry-After"));
    if (Number.isFinite(seconds) && seconds >= 0) {
      retryAfter = Math.ceil(seconds);
      message = `${message} Try again in ${retryAfter} second${retryAfter === 1 ? "" : "s"}.`;
    }
  }
  return new ChatStreamError(response.status, message, retryAfter);
}

function isAbortError(err: unknown): boolean {
  return err instanceof DOMException
    ? err.name === "AbortError"
    : (err as { name?: string } | null)?.name === "AbortError";
}

export interface ChatStreamHandlers {
  onStart?: (event: MessageStartEvent) => void;
  onToken?: (text: string) => void;
  /** Terminal: the turn failed after the stream opened; nothing was saved for the assistant. */
  onError?: (event: StreamErrorEvent) => void;
  /** Terminal, success. */
  onEnd?: (event: MessageEndEvent) => void;
}

/**
 * Sends a message and streams the assistant's reply over SSE.
 *
 * Uses fetch + ReadableStream rather than axios (which buffers the whole body)
 * or EventSource (which can neither POST nor send the Authorization header).
 *
 * Resolves when a terminal event arrives or the request is aborted (an abort is
 * silent). Rejects with ChatStreamError for a non-2xx response, a network
 * failure, or a stream that closes without a terminal event.
 */
export async function streamChatMessage(
  conversationId: string,
  content: string,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const token = localStorage.getItem("access_token");

  let response: Response;
  try {
    response = await fetch(`/api/v1/chat/conversations/${conversationId}/messages`, {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    });
  } catch (err) {
    if (isAbortError(err)) return;
    throw new ChatStreamError(0, NETWORK_ERROR_MESSAGE);
  }

  if (!response.ok) {
    if (response.status === 401) {
      // Mirror the axios response interceptor in client.ts
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    throw await errorFromResponse(response);
  }

  if (!response.body) {
    throw new ChatStreamError(0, "The server sent an empty response.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = createSSEParser();
  let finished = false;

  // Returns true once a terminal event has been dispatched.
  const dispatch = (events: ReturnType<typeof parser.push>): boolean => {
    for (const { event, data } of events) {
      switch (event) {
        case "message_start":
          handlers.onStart?.(data as MessageStartEvent);
          break;
        case "token": {
          const text = (data as { text?: unknown } | null)?.text;
          if (typeof text === "string" && text) handlers.onToken?.(text);
          break;
        }
        case "error":
          handlers.onError?.(data as StreamErrorEvent);
          return true;
        case "message_end":
          handlers.onEnd?.(data as MessageEndEvent);
          return true;
        default:
          // tool_start, tool_end, clarification, confirm_required and any
          // future event names: ignored by contract
          break;
      }
    }
    return false;
  };

  try {
    while (!finished) {
      const { done, value } = await reader.read();
      if (done) {
        // End-of-stream flush of the decoder (emits any buffered partial bytes)
        finished = dispatch(parser.push(decoder.decode()));
        if (!finished) finished = dispatch(parser.flush());
        if (!finished) {
          throw new ChatStreamError(0, "The connection closed before the reply finished.");
        }
        break;
      }
      finished = dispatch(parser.push(decoder.decode(value, { stream: true })));
    }
  } catch (err) {
    if (isAbortError(err) || signal?.aborted) return;
    if (err instanceof ChatStreamError) throw err;
    throw new ChatStreamError(0, "The connection was interrupted before the reply finished.");
  } finally {
    // Stop the body download (no-op if it already ended) and free the stream
    try {
      await reader.cancel();
    } catch {
      // already closed or errored
    }
    try {
      reader.releaseLock();
    } catch {
      // already released
    }
  }
}
