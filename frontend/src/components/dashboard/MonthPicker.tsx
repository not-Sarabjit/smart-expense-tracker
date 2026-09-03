/**
 * MonthPicker — navigation control for the Dashboard month selector.
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
 */

interface MonthPickerProps {
  year: number;
  month: number; // 1–12
  isAllTime: boolean;
  onPrev: () => void;
  onNext: () => void;
  onToggleAllTime: () => void;
}

/**
 * Formats the given year and 1-based month as "MMMM YYYY" (e.g. "June 2025")
 * using the browser's built-in `Intl.DateTimeFormat` — no external library needed.
 */
function formatMonthYear(year: number, month: number): string {
  // Use the 1st of the month; month is 0-based in Date constructor
  const date = new Date(year, month - 1, 1);
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(date);
}

/**
 * Returns the current calendar year and month (1-based) based on the client
 * clock. Kept in a helper so it is easy to stub in tests.
 */
function getCurrentYearMonth(): { currentYear: number; currentMonth: number } {
  const now = new Date();
  return { currentYear: now.getFullYear(), currentMonth: now.getMonth() + 1 };
}

export default function MonthPicker({
  year,
  month,
  isAllTime,
  onPrev,
  onNext,
  onToggleAllTime,
}: MonthPickerProps) {
  const { currentYear, currentMonth } = getCurrentYearMonth();

  // "Next" must be disabled when the selected month IS the current calendar month (Req 6.6)
  const isCurrentMonth = year === currentYear && month === currentMonth;

  // Both navigation buttons are disabled when "All Time" is active (Req 6.7)
  const navDisabled = isAllTime;
  const nextDisabled = isAllTime || isCurrentMonth;

  // Shared classes for the prev/next chevron buttons
  const navButtonBase =
    "flex items-center justify-center w-8 h-8 rounded-full transition-colors " +
    "text-gray-600 dark:text-gray-300 " +
    "hover:bg-gray-100 dark:hover:bg-gray-700 " +
    "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent dark:disabled:hover:bg-transparent";

  return (
    <div className="flex flex-wrap items-center gap-2 sm:gap-4">
      {/* ← Previous month button (Req 6.2, 6.3) */}
      <button
        type="button"
        onClick={onPrev}
        disabled={navDisabled}
        aria-label="Previous month"
        className={navButtonBase}
      >
        {/* Left chevron */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      {/* Month / year label (Req 6.1) */}
      <span
        className={
          "min-w-[10rem] text-center text-base font-semibold select-none " +
          (isAllTime
            ? "text-gray-400 dark:text-gray-500"
            : "text-gray-800 dark:text-gray-100")
        }
        aria-live="polite"
        aria-atomic="true"
      >
        {isAllTime ? "All Time" : formatMonthYear(year, month)}
      </span>

      {/* → Next month button (Req 6.2, 6.4, 6.6) */}
      <button
        type="button"
        onClick={onNext}
        disabled={nextDisabled}
        aria-label="Next month"
        className={navButtonBase}
      >
        {/* Right chevron */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>

      {/* "All Time" toggle button (Req 6.7, 6.8) */}
      <button
        type="button"
        onClick={onToggleAllTime}
        aria-pressed={isAllTime}
        aria-label={isAllTime ? "Disable All Time filter" : "Enable All Time filter"}
        className={
          "ml-2 px-3 py-1.5 text-sm font-medium rounded-full border transition-colors " +
          (isAllTime
            ? // Active state — filled indigo
              "bg-indigo-600 dark:bg-indigo-500 text-white border-indigo-600 dark:border-indigo-500 " +
              "hover:bg-indigo-700 dark:hover:bg-indigo-600"
            : // Inactive state — outlined
              "bg-transparent text-indigo-600 dark:text-indigo-400 border-indigo-300 dark:border-indigo-600 " +
              "hover:bg-indigo-50 dark:hover:bg-indigo-900/30")
        }
      >
        All Time
      </button>
    </div>
  );
}
