import { MonthlySummary } from "../../types";
import { LoadingSpinner } from "../ui/LoadingSpinner";
import { formatCurrency } from "../../utils/formatters";

interface SummaryCardsProps {
  summary: MonthlySummary | null;
  loading: boolean;
  error: string | null;
}

interface CardConfig {
  title: string;
  amount: number;
  /** Tailwind text colour classes for the amount */
  amountClass: string;
  /** Tailwind border accent class */
  accentClass: string;
}

/**
 * Renders three summary cards: Total Income, Total Expenses, and Net Balance.
 *
 * Requirements: 5.1, 5.3, 5.4, 5.5, 5.6, 5.7
 */
export function SummaryCards({ summary, loading, error }: SummaryCardsProps) {
  // --- Error state: single banner spanning all three cards (Req 5.6) ---
  if (error) {
    return (
      <div
        role="alert"
        className="col-span-3 rounded-lg border border-red-300 bg-red-50 px-6 py-4 text-red-700 dark:border-red-700 dark:bg-red-900/20 dark:text-red-400"
      >
        <p className="font-medium">Failed to load summary</p>
        <p className="mt-1 text-sm">{error}</p>
      </div>
    );
  }

  // Net balance colour: blue for ≥ 0, red for < 0 (Req 5.3, 5.4)
  const net = summary?.net ?? 0;
  const netAmountClass =
    net < 0
      ? "text-red-500 dark:text-red-400"
      : "text-blue-600 dark:text-blue-400";

  const cards: CardConfig[] = [
    {
      title: "Total Income",
      amount: summary?.total_income ?? 0,
      amountClass: "text-green-600 dark:text-green-400",
      accentClass: "border-t-green-500",
    },
    {
      title: "Total Expenses",
      amount: summary?.total_expense ?? 0,
      amountClass: "text-red-500 dark:text-red-400",
      accentClass: "border-t-red-500",
    },
    {
      title: "Net Balance",
      amount: net,
      amountClass: netAmountClass,
      accentClass: net < 0 ? "border-t-red-500" : "border-t-blue-500",
    },
  ];

  return (
    <>
      {cards.map((card) => (
        <div
          key={card.title}
          className={`rounded-lg border border-t-4 border-gray-200 bg-white p-6 shadow-sm
            dark:border-gray-700 dark:bg-gray-800 ${card.accentClass}`}
        >
          <h3 className="text-sm font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {card.title}
          </h3>

          {/* Loading state: spinner in place of the amount (Req 5.5) */}
          {loading ? (
            <div className="mt-3 flex items-center justify-center" aria-label="Loading">
              <LoadingSpinner size={6} />
            </div>
          ) : (
            // Amount formatted with exactly two decimal places (Req 5.7)
            <p className={`mt-2 text-2xl font-bold ${card.amountClass}`}>
              {formatCurrency(card.amount)}
            </p>
          )}
        </div>
      ))}
    </>
  );
}

export default SummaryCards;
