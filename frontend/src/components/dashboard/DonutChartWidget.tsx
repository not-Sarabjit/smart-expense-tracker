import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Transaction, Category } from "@/types";

/** Fixed colour palette for pie slices (Tailwind-compatible hex values) */
const SLICE_COLOURS = [
  "#6366f1", // indigo-500
  "#f59e0b", // amber-500
  "#10b981", // emerald-500
  "#3b82f6", // blue-500
  "#ec4899", // pink-500
  "#f97316", // orange-500
  "#8b5cf6", // violet-500
  "#14b8a6", // teal-500
  "#ef4444", // red-500
  "#84cc16", // lime-500
];

/** Returns true when the <html> element carries the "dark" class */
function isDarkMode(): boolean {
  return document.documentElement.classList.contains("dark");
}

interface DonutChartWidgetProps {
  /** All transactions for the selected period — filtered internally to expenses */
  transactions: Transaction[];
  /** Category list used to resolve category names from IDs */
  categories: Category[];
}

interface SliceEntry {
  name: string;
  value: number;
  fill: string;
}

/**
 * Renders a donut-style PieChart of expense transactions grouped by category.
 *
 * - Filters `transactions` to `type === "expense"` internally
 * - Groups by `category_id`, summing `amount` per group
 * - Maps each group to `{ name, value, fill }` using the `categories` prop to
 *   resolve names and a fixed colour palette for fills
 * - Renders a custom legend listing each category name with its colour dot
 * - Falls back to `EmptyState` when there are no expense transactions
 *
 * Requirements: 7.2, 7.4, 7.5, 7.6
 */
export function DonutChartWidget({ transactions, categories }: DonutChartWidgetProps) {
  // Filter to expenses only
  const expenseTransactions = transactions.filter((tx) => tx.type === "expense");

  // Show EmptyState when there are no expense transactions (Requirement 7.4)
  if (expenseTransactions.length === 0) {
    return (
      <EmptyState message="No expense transactions found for this period." />
    );
  }

  // Build a lookup map from category_id → category name
  const categoryMap = new Map<number, string>(
    categories.map((cat) => [cat.id, cat.name])
  );

  // Group by category_id (null = uncategorised) and sum amounts
  const grouped = new Map<number | null, number>();
  for (const tx of expenseTransactions) {
    grouped.set(tx.category_id, (grouped.get(tx.category_id) ?? 0) + tx.amount);
  }

  // Map to slice entries with resolved names and assigned colours
  const slices: SliceEntry[] = Array.from(grouped.entries()).map(
    ([categoryId, total], index) => ({
      name:
        categoryId === null
          ? "Uncategorised"
          : categoryMap.get(categoryId) ?? `Category ${categoryId}`,
      value: total,
      fill: SLICE_COLOURS[index % SLICE_COLOURS.length],
    })
  );

  // Recharts uses inline styles, so we read the current dark-mode state to
  // apply correct tooltip colours — Tailwind `dark:` variants cannot reach
  // into Recharts' inline contentStyle.
  const dark = isDarkMode();
  const tooltipStyle = dark
    ? {
        borderRadius: "0.375rem",
        border: "1px solid #374151",   // gray-700
        backgroundColor: "#1f2937",    // gray-800
        color: "#f3f4f6",              // gray-100
      }
    : {
        borderRadius: "0.375rem",
        border: "1px solid #e5e7eb",   // gray-200
        backgroundColor: "#ffffff",
        color: "#111827",              // gray-900
      };

  return (
    <div className="flex flex-col items-center gap-4 w-full min-w-0 rounded-lg bg-white dark:bg-gray-800 p-4">
      {/* Donut chart (Requirement 7.2) */}
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
            >
              {slices.map((slice, index) => (
                <Cell key={`cell-${index}`} fill={slice.fill} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [
                `$${Number(value ?? 0).toFixed(2)}`,
              ]}
              contentStyle={tooltipStyle}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Custom legend displaying each category name alongside its colour (Requirement 7.6) */}
      <ul className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-sm text-gray-700 dark:text-gray-300">
        {slices.map((slice, index) => (
          <li key={index} className="flex items-center gap-1.5">
            <span
              className="inline-block h-3 w-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: slice.fill }}
              aria-hidden="true"
            />
            <span>{slice.name}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default DonutChartWidget;
