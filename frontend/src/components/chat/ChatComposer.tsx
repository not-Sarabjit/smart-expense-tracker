import { useLayoutEffect, useRef, useState } from "react";
import { MAX_MESSAGE_LENGTH } from "../../api/chat";

/** ~6 rows of text-sm (20px line height) plus py-2 padding. */
const MAX_TEXTAREA_PX = 6 * 20 + 16;

interface ChatComposerProps {
  streaming: boolean;
  /** Disables input entirely (e.g. while the transcript loads). */
  disabled?: boolean;
  onSend: (content: string) => void;
  onStop: () => void;
}

/**
 * Message input: auto-growing textarea, live character counter, Enter to send,
 * Shift+Enter for a newline. While a reply streams, Send becomes Stop.
 */
export function ChatComposer({ streaming, disabled = false, onSend, onStop }: ChatComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const length = value.length;
  const tooLong = length > MAX_MESSAGE_LENGTH;
  const canSend = !streaming && !disabled && !tooLong && value.trim().length > 0;

  // Grow with the content up to MAX_TEXTAREA_PX, then scroll
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_PX)}px`;
  }, [value]);

  // Hand focus back once a reply finishes
  useLayoutEffect(() => {
    if (!streaming && !disabled) textareaRef.current?.focus();
  }, [streaming, disabled]);

  function submit() {
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 sm:px-6 py-3"
    >
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2">
          <label htmlFor="chat-composer" className="sr-only">
            Message
          </label>
          <textarea
            id="chat-composer"
            ref={textareaRef}
            rows={1}
            value={value}
            disabled={streaming || disabled}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={streaming ? "Waiting for the reply…" : "Ask about your expenses…"}
            aria-invalid={tooLong}
            aria-describedby="chat-composer-count"
            className={`flex-1 resize-none rounded-lg border px-3 py-2 text-sm leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed transition-colors ${
              tooLong ? "border-red-400 dark:border-red-500" : "border-gray-300 dark:border-gray-600"
            }`}
          />

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              className="shrink-0 rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!canSend}
              className="shrink-0 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              Send
            </button>
          )}
        </div>

        <div className="mt-1 flex justify-between text-xs">
          <span className="text-gray-400 dark:text-gray-500 hidden sm:inline">
            Enter to send · Shift+Enter for a new line
          </span>
          <span
            id="chat-composer-count"
            className={`ml-auto tabular-nums ${
              tooLong ? "text-red-500 dark:text-red-400 font-medium" : "text-gray-400 dark:text-gray-500"
            }`}
          >
            {length}/{MAX_MESSAGE_LENGTH}
          </span>
        </div>
      </div>
    </form>
  );
}

export default ChatComposer;
