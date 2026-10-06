import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { createSSEParser, type SSEEvent } from "../api/sse";

function record(event: string, data: unknown, nl = "\n"): string {
  return `event: ${event}${nl}data: ${JSON.stringify(data)}${nl}${nl}`;
}

describe("createSSEParser", () => {
  it("parses a single complete event", () => {
    const parser = createSSEParser();
    expect(parser.push(record("token", { text: "Hi" }))).toEqual([
      { event: "token", data: { text: "Hi" } },
    ]);
  });

  it("parses two events in one push", () => {
    const parser = createSSEParser();
    const events = parser.push(
      record("message_start", { conversation_id: "abc", user_message_id: 1, prompt_version: "v1" }) +
        record("token", { text: "Hello" })
    );
    expect(events.map((e) => e.event)).toEqual(["message_start", "token"]);
    expect(events[1].data).toEqual({ text: "Hello" });
  });

  it("handles \\r\\n line endings", () => {
    const parser = createSSEParser();
    expect(
      parser.push(record("token", { text: "a" }, "\r\n") + record("message_end", { message_id: 2 }, "\r\n"))
    ).toEqual([
      { event: "token", data: { text: "a" } },
      { event: "message_end", data: { message_id: 2 } },
    ]);
  });

  it("handles a \\r\\n split between two chunks", () => {
    const parser = createSSEParser();
    expect(parser.push('event: token\r\ndata: {"text":"x"}\r\n\r')).toEqual([]);
    expect(parser.push("\n")).toEqual([{ event: "token", data: { text: "x" } }]);
  });

  it("defaults the event name to 'message'", () => {
    const parser = createSSEParser();
    expect(parser.push('data: {"a":1}\n\n')).toEqual([{ event: "message", data: { a: 1 } }]);
  });

  it("yields an event split across three pushes once, only after the blank line", () => {
    const parser = createSSEParser();
    expect(parser.push("event: tok")).toEqual([]);
    expect(parser.push('en\ndata: {"text":"spl')).toEqual([]);
    expect(parser.push('it"}\n')).toEqual([]);
    expect(parser.push("\n")).toEqual([{ event: "token", data: { text: "split" } }]);
    expect(parser.push("")).toEqual([]);
    expect(parser.flush()).toEqual([]);
  });

  it("ignores comment lines and passes unknown event names through without throwing", () => {
    const parser = createSSEParser();
    let events: SSEEvent[] = [];
    expect(() => {
      events = parser.push(
        ":keep-alive\n\n" +
          record("tool_start", { name: "x" }) +
          ": inline comment\nevent: token\ndata: {\"text\":\"ok\"}\n\n" +
          record("some_future_event", { whatever: true })
      );
    }).not.toThrow();
    expect(events).toEqual([
      { event: "tool_start", data: { name: "x" } },
      { event: "token", data: { text: "ok" } },
      { event: "some_future_event", data: { whatever: true } },
    ]);
  });

  it("skips malformed JSON instead of throwing", () => {
    const parser = createSSEParser();
    let events: SSEEvent[] = [];
    expect(() => {
      events = parser.push("event: token\ndata: {not json\n\n" + record("token", { text: "after" }));
    }).not.toThrow();
    expect(events).toEqual([{ event: "token", data: { text: "after" } }]);
  });

  it("flush() returns a final event that lacked its terminating blank line", () => {
    const parser = createSSEParser();
    expect(parser.push('event: message_end\ndata: {"message_id":9}')).toEqual([]);
    expect(parser.flush()).toEqual([{ event: "message_end", data: { message_id: 9 } }]);
    expect(parser.flush()).toEqual([]);
  });

  // ── Property: arbitrary chunking never changes the parsed sequence ─────────

  const eventArb = fc.record({
    event: fc.stringMatching(/^[a-z_]{1,16}$/),
    data: fc.jsonValue(),
    newline: fc.constantFrom("\n", "\r\n"),
    comment: fc.option(fc.stringMatching(/^[ -~]{0,12}$/), { nil: undefined }),
  });

  it("yields exactly the original events for any chunking of the stream", () => {
    fc.assert(
      fc.property(
        fc.array(eventArb, { maxLength: 15 }),
        fc.array(fc.nat(), { maxLength: 30 }),
        (events, rawCuts) => {
          const wire = events
            .map(({ event, data, newline, comment }) =>
              (comment !== undefined ? `:${comment}${newline}` : "") + record(event, data, newline)
            )
            .join("");

          const cuts = [...new Set(rawCuts.map((c) => c % (wire.length + 1)))].sort((a, b) => a - b);
          const chunks: string[] = [];
          let prev = 0;
          for (const cut of cuts) {
            chunks.push(wire.slice(prev, cut));
            prev = cut;
          }
          chunks.push(wire.slice(prev));

          const parser = createSSEParser();
          const out: SSEEvent[] = [];
          for (const chunk of chunks) out.push(...parser.push(chunk));
          out.push(...parser.flush());

          // Compare against a JSON round-trip (e.g. -0 serialises as 0)
          expect(out).toEqual(
            events.map(({ event, data }) => ({
              event,
              data: JSON.parse(JSON.stringify(data)),
            }))
          );
        }
      ),
      { numRuns: 500 }
    );
  });
});
