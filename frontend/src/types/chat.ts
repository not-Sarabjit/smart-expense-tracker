// ─── Chat REST resources ──────────────────────────────────────────────────────

/** ConversationOut — `id` is a UUID string on the wire. */
export interface Conversation {
  id: string;
  title: string | null;
  archived: boolean;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export type ChatRole = "user" | "assistant" | "system" | "tool";

/** MessageOut — `content` is null for a tool-only assistant turn. */
export interface ChatMessage {
  /** Server id; a negative id marks an optimistic message not yet confirmed by message_start. */
  id: number;
  conversation_id: string;
  role: ChatRole;
  content: string | null;
  tool_calls: unknown | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}

/** One page of conversations; `total` comes from the X-Total-Count response header. */
export interface ConversationPage {
  items: Conversation[];
  total: number;
}

/** One page of messages (oldest first); `total` comes from X-Total-Count. */
export interface ChatMessagePage {
  items: ChatMessage[];
  total: number;
}

// --- Request payloads ---

export interface ConversationCreatePayload {
  title?: string;
}

/** PATCH body — only the fields sent are applied; at least one is required. */
export interface ConversationUpdatePayload {
  title?: string;
  archived?: boolean;
}

// ─── SSE event payloads (POST …/messages stream) ─────────────────────────────

export interface MessageStartEvent {
  conversation_id: string;
  user_message_id: number;
  prompt_version: string;
}

export interface TokenEvent {
  text: string;
}

/** Terminal: nothing was persisted for the assistant turn. */
export interface StreamErrorEvent {
  message: string;
  request_id: string;
}

/** Terminal, success. `title` is set only when the conversation was just auto-titled. */
export interface MessageEndEvent {
  message_id: number;
  model: string;
  usage: Record<string, unknown> | null;
  latency_ms: number;
  title: string | null;
}
