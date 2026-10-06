import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { ChatStreamHandlers } from "../api/chat";

vi.mock("../api/chat", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/chat")>();
  return {
    ...actual,
    getAllMessages: vi.fn(),
    streamChatMessage: vi.fn(),
  };
});

import { getAllMessages, streamChatMessage } from "../api/chat";
import { useChat } from "../hooks/useChat";

const CONV_ID = "11111111-2222-3333-4444-555555555555";

describe("useChat — optimistic send", () => {
  let handlers: ChatStreamHandlers = {};
  let finishStream: () => void = () => {};

  beforeEach(() => {
    vi.mocked(getAllMessages).mockReset().mockResolvedValue({ items: [], total: 0 });
    vi.mocked(streamChatMessage)
      .mockReset()
      .mockImplementation((_id, _content, h) => {
        handlers = h;
        return new Promise<void>((resolve) => {
          finishStream = resolve;
        });
      });
  });

  it("swaps the temporary negative id for user_message_id and appends the reply", async () => {
    const onTurnComplete = vi.fn();
    const { result } = renderHook(() => useChat(CONV_ID, { onTurnComplete }));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let sendPromise: Promise<void> = Promise.resolve();
    act(() => {
      sendPromise = result.current.send("  How much did I spend on food?  ");
    });

    // Optimistic: trimmed content, negative temporary id, streaming
    expect(streamChatMessage).toHaveBeenCalledWith(
      CONV_ID,
      "How much did I spend on food?",
      expect.any(Object),
      expect.any(AbortSignal)
    );
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].id).toBeLessThan(0);
    expect(result.current.messages[0].content).toBe("How much did I spend on food?");
    expect(result.current.streaming).toBe(true);

    act(() => {
      handlers.onStart?.({ conversation_id: CONV_ID, user_message_id: 42, prompt_version: "v1" });
    });
    expect(result.current.messages[0].id).toBe(42);

    act(() => {
      handlers.onToken?.("You spent ");
      handlers.onToken?.("**$120**.");
    });
    expect(result.current.streamingText).toBe("You spent **$120**.");

    act(() => {
      handlers.onEnd?.({
        message_id: 43,
        model: "fake",
        usage: null,
        latency_ms: 5,
        title: "Food spending",
      });
      finishStream();
    });
    await act(() => sendPromise);

    expect(result.current.messages.map((m) => [m.id, m.role, m.content])).toEqual([
      [42, "user", "How much did I spend on food?"],
      [43, "assistant", "You spent **$120**."],
    ]);
    expect(result.current.streamingText).toBe("");
    expect(result.current.streaming).toBe(false);
    expect(onTurnComplete).toHaveBeenCalledWith(CONV_ID, "Food spending");
  });

  it("keeps the user message and drops partial text on an error event", async () => {
    const { result } = renderHook(() => useChat(CONV_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let sendPromise: Promise<void> = Promise.resolve();
    act(() => {
      sendPromise = result.current.send("hello");
    });
    act(() => {
      handlers.onStart?.({ conversation_id: CONV_ID, user_message_id: 7, prompt_version: "v1" });
      handlers.onToken?.("partial");
      handlers.onError?.({ message: "The assistant could not finish.", request_id: "req-123" });
      finishStream();
    });
    await act(() => sendPromise);

    expect(result.current.messages.map((m) => m.id)).toEqual([7]);
    expect(result.current.streamingText).toBe("");
    expect(result.current.error).toEqual({
      message: "The assistant could not finish.",
      requestId: "req-123",
    });
  });
});
