import { memo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatRole } from "../../types";

interface MessageBubbleProps {
  role: ChatRole;
  content: string | null;
  /** Shown under the bubble in small print, e.g. "Stopped". */
  note?: string;
}

/**
 * Markdown element styling for assistant replies. Raw HTML in model output is
 * never rendered: react-markdown escapes it by default and no rehype-raw is used.
 */
const markdownComponents: Components = {
  h1: ({ children }) => <h1 className="mt-4 mb-2 text-lg font-bold first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="mt-4 mb-2 text-base font-bold first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-3 mb-1.5 text-sm font-semibold first:mt-0">{children}</h3>,
  h4: ({ children }) => <h4 className="mt-3 mb-1 text-sm font-semibold first:mt-0">{children}</h4>,
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc pl-5 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal pl-5 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="pl-0.5">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-4 border-gray-300 dark:border-gray-600 pl-3 text-gray-600 dark:text-gray-400">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-gray-200 dark:border-gray-700" />,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className="text-indigo-600 dark:text-indigo-400 underline hover:text-indigo-700 dark:hover:text-indigo-300"
    >
      {children}
    </a>
  ),
  // Don't auto-load remote images from model output; show them as links instead
  img: ({ src, alt }) =>
    typeof src === "string" && src ? (
      <a
        href={src}
        target="_blank"
        rel="noopener noreferrer nofollow"
        className="text-indigo-600 dark:text-indigo-400 underline"
      >
        {alt || "image"}
      </a>
    ) : null,
  // Inline code. Inside <pre> the overrides on `pre` below reset these styles.
  code: ({ className, children }) => (
    <code
      className={`rounded bg-gray-100 dark:bg-gray-900 px-1 py-0.5 font-mono text-[0.85em] ${className ?? ""}`}
    >
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg bg-gray-900 dark:bg-black/60 p-3 font-mono text-xs leading-relaxed text-gray-100 [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-[1em] [&_code]:text-inherit">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
      <table className="min-w-full text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-gray-50 dark:bg-gray-900/60">{children}</thead>,
  tr: ({ children }) => (
    <tr className="border-b border-gray-200 dark:border-gray-700 last:border-b-0">{children}</tr>
  ),
  th: ({ children, style }) => (
    <th style={style} className="px-3 py-2 text-left font-semibold whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children, style }) => (
    <td style={style} className="px-3 py-2 align-top">
      {children}
    </td>
  ),
};

/** Renders assistant markdown. Memoised so earlier bubbles don't re-parse on every token. */
export const AssistantMarkdown = memo(function AssistantMarkdown({ text }: { text: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {text}
    </ReactMarkdown>
  );
});

/**
 * One chat message. User messages are right-aligned plain text; assistant
 * messages are left-aligned markdown. System/tool messages and messages
 * without text content render nothing.
 */
export function MessageBubble({ role, content, note }: MessageBubbleProps) {
  if (content === null || content === "") return null;
  if (role !== "user" && role !== "assistant") return null;

  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-br-sm bg-indigo-600 dark:bg-indigo-500 px-4 py-2.5 text-sm text-white whitespace-pre-wrap break-words">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start">
      <div className="max-w-[90%] sm:max-w-[80%] min-w-0 rounded-2xl rounded-bl-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-2.5 text-sm text-gray-800 dark:text-gray-100 break-words">
        <AssistantMarkdown text={content} />
      </div>
      {note && <span className="mt-1 ml-1 text-xs text-gray-400 dark:text-gray-500">{note}</span>}
    </div>
  );
}

export default MessageBubble;
