/**
 * Incremental Server-Sent Events parser for the chat stream.
 *
 * Pure: no DOM, no fetch. Feed it decoded text in whatever chunks the network
 * delivers; it returns each event once its terminating blank line has arrived
 * and keeps any trailing partial event buffered for the next push().
 *
 * Wire format (one record): "event: <name>\n" + "data: <json>\n" + "\n".
 * Lines may end in "\n" or "\r\n"; lines starting with ":" are comments.
 */

export type SSEEvent = { event: string; data: unknown };

const DEFAULT_EVENT = "message";

/**
 * Normalises line endings to "\n". A trailing lone "\r" is left in place: it may
 * be the first half of a "\r\n" whose "\n" arrives in the next chunk.
 */
function normaliseNewlines(text: string): string {
  return text.replace(/\r\n/g, "\n").replace(/\r(?!$)/g, "\n");
}

/** Parses one complete record (no blank lines inside). Returns null to skip it. */
function parseBlock(block: string): SSEEvent | null {
  let event = DEFAULT_EVENT;
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line === "" || line.startsWith(":")) continue; // blank or comment

    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") event = value || DEFAULT_EVENT;
    else if (field === "data") dataLines.push(value);
    // id:, retry: and unknown fields are irrelevant here
  }

  // A record without data (e.g. comment-only keep-alive) dispatches nothing
  if (dataLines.length === 0) return null;

  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null; // malformed JSON — skip the event, never throw
  }
}

export function createSSEParser(): {
  push(text: string): SSEEvent[];
  flush(): SSEEvent[];
} {
  let buffer = "";

  function drain(): SSEEvent[] {
    const events: SSEEvent[] = [];
    let end = buffer.indexOf("\n\n");
    while (end !== -1) {
      const parsed = parseBlock(buffer.slice(0, end));
      if (parsed) events.push(parsed);
      buffer = buffer.slice(end + 2);
      end = buffer.indexOf("\n\n");
    }
    return events;
  }

  return {
    push(text: string): SSEEvent[] {
      buffer = normaliseNewlines(buffer + text);
      return drain();
    },

    /** Call once the stream has ended: parses a final record that lacked its blank line. */
    flush(): SSEEvent[] {
      const rest = buffer.replace(/\r$/, "");
      buffer = "";
      const parsed = rest.trim() === "" ? null : parseBlock(rest);
      return parsed ? [parsed] : [];
    },
  };
}
