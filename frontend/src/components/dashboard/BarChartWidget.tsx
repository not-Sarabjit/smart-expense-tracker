import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { EmptyState } from "@/components/ui/EmptyState";

interface BarChartWidgetProps {
  /** Total income amount for the selected period */
  totalIncome: number;
  /** Total expense amount for the selected period */
  totalExpense: number;
}

/** Returns true when the <html> element carries the "dark" class */
function isDarkMode(): boolean {
  return document.documentElement.classList.contains("dark");
}

/** Bar fill colours: green-600 for income, red-500 for expense */
const BAR_FILLS = ["#16a34a", "#ef4444"];

/**
 * Renders a bar chart comparing total income vs total expenses.
 *
 * - Two bars: green (income) and red (expense)
 * - Labelled X and Y axes
 * - Falls back to EmptyState when both values are zero
 *
 * Requirements: 7.1, 7.3, 7.6
 */
export function BarChartWidget({ totalIncome, totalExpense }: BarChartWidgetProps) {
  if (totalIncome === 0 && totalExpense === 0) {
    return <EmptyState message="No transactions found for this period." />;
  }

  const data = [
    { label: "Income", value: totalIncome },
    { label: "Expense", value: totalExpense },
  ];

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

  const gridStroke = dark ? "#374151" : "#e5e7eb"; // gray-700 / gray-200

  return (
    <div className="h-64 w-full min-w-0 rounded-lg bg-white dark:bg-gray-800 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
          barCategoryGap="40%"
        >
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
          <XAxis
            dataKey="label"
            tick={{ fill: "currentColor", fontSize: 13 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "currentColor", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={60}
            tickFormatter={(v: number) =>
              v >= 1_000_000
                ? `${(v / 1_000_000).toFixed(1)}M`
                : v >= 1_000
                ? `${(v / 1_000).toFixed(0)}k`
                : v.toString()
            }
          />
          <Tooltip
            contentStyle={tooltipStyle}
          />
          {/* Single Bar with per-entry Cell fills: green-600 income, red-500 expense */}
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={BAR_FILLS[index]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default BarChartWidget;
