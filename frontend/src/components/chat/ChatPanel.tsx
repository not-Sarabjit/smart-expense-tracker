import { useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

interface ChatPanelProps {
  sidebar: ReactNode;
  /** Shown in the transcript header next to the mobile sidebar toggle. */
  title?: ReactNode;
  children: ReactNode;
}

/**
 * Two-column chat layout filling the viewport under the Navbar (h-16).
 * At md and up the sidebar is always visible; below md it collapses behind a
 * toggle and closes again whenever the route changes.
 */
export function ChatPanel({ sidebar, title, children }: ChatPanelProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  return (
    <div className="flex h-[calc(100dvh-4rem)] bg-gray-50 dark:bg-gray-900">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 top-16 z-30 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        id="chat-sidebar"
        className={`${
          sidebarOpen ? "flex" : "hidden"
        } md:flex fixed md:static top-16 bottom-0 left-0 z-40 w-72 max-w-[85vw] shrink-0 flex-col border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900`}
        aria-label="Conversations"
      >
        {sidebar}
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 sm:px-6">
          <button
            type="button"
            onClick={() => setSidebarOpen((prev) => !prev)}
            className="md:hidden -ml-2 p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Toggle conversations"
            aria-expanded={sidebarOpen}
            aria-controls="chat-sidebar"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <h1 className="truncate text-sm font-semibold text-gray-900 dark:text-white">
            {title ?? "Chat"}
          </h1>
        </header>

        {children}
      </section>
    </div>
  );
}

export default ChatPanel;
