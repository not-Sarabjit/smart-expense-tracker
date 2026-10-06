import { describe, it, expect, vi, afterEach } from "vitest";
import { streamChatMessage, ChatStreamError } from "../api/chat";

const CONV_ID = "11111111-2222-3333-4444-555555555555";

/** A streaming Response whose body yields `chunks` as UTF-8 bytes. */
function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("streamChatMessage", () => {
  it("sends the bearer token and dispatches events across chunk (and UTF-8) boundaries", async () => {
    localStorage.setItem("access_token", "tok");
    const bytes = new TextEncoder().encode('event: token\ndata: {"text":"₹5"}\n\n');
    // Split inside the 3-byte "₹" to exercise TextDecoder {stream:true}
    const cut = bytes.indexOf(0xe2) + 1;
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream<Uint8Array>({
          start(c) {
            c.enqueue(new TextEncoder().encode(
              'event: message_start\ndata: {"conversation_id":"x","user_message_id":1,"prompt_version":"v"}\n\n: ping\n\nevent: tool_start\ndata: {}\n\n'
            ));
            c.enqueue(bytes.slice(0, cut));
            c.enqueue(bytes.slice(cut));
            c.enqueue(new TextEncoder().encode(
              'event: message_end\r\ndata: {"message_id":2,"model":"m","usage":null,"latency_ms":1,"title":null}\r\n\r\n'
            ));
            c.close();
          },
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const onStart = vi.fn();
    const onToken = vi.fn();
    const onEnd = vi.fn();
    await streamChatMessage(CONV_ID, "hi", { onStart, onToken, onEnd });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/v1/chat/conversations/${CONV_ID}/messages`);
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer tok");
    expect(JSON.parse(init.body)).toEqual({ content: "hi" });

    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ user_message_id: 1 }));
    expect(onToken).toHaveBeenCalledWith("₹5");
    expect(onEnd).toHaveBeenCalledWith(expect.objectContaining({ message_id: 2 }));
  });

  it("calls onError for an error event", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        sseResponse(['event: error\ndata: {"message":"boom","request_id":"r1"}\n\n'])
      )
    );
    const onError = vi.fn();
    await streamChatMessage(CONV_ID, "hi", { onError });
    expect(onError).toHaveBeenCalledWith({ message: "boom", request_id: "r1" });
  });

  it("throws a ChatStreamError carrying Retry-After on 429", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: true, message: "Too many messages.", status_code: 429 }), {
          status: 429,
          headers: { "Retry-After": "17", "Content-Type": "application/json" },
        })
      )
    );
    const err = await streamChatMessage(CONV_ID, "hi", {}).catch((e) => e);
    expect(err).toBeInstanceOf(ChatStreamError);
    expect(err.status).toBe(429);
    expect(err.retryAfter).toBe(17);
    expect(err.message).toBe("Too many messages. Try again in 17 seconds.");
  });

  it("throws status 503 when the assistant is disabled", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "AI Assistant is currently disabled" }), { status: 503 })
      )
    );
    const err = await streamChatMessage(CONV_ID, "hi", {}).catch((e) => e);
    expect(err.status).toBe(503);
    expect(err.message).toBe("AI Assistant is currently disabled");
  });

  it("rejects when the stream closes without a terminal event", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse(['event: token\ndata: {"text":"a"}\n\n'])));
    await expect(streamChatMessage(CONV_ID, "hi", {})).rejects.toBeInstanceOf(ChatStreamError);
  });

  it("resolves quietly when aborted", async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError"))
            );
          })
      )
    );
    const pending = streamChatMessage(CONV_ID, "hi", {}, controller.signal);
    controller.abort();
    await expect(pending).resolves.toBeUndefined();
  });
});
