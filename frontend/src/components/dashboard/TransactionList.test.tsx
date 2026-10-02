import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TransactionList, LIST_PAGE_SIZE } from "./TransactionList";
import type { Transaction } from "@/types";

function tx(id: number, overrides: Partial<Transaction> = {}): Transaction {
  return {
    id,
    amount: 10,
    date: "2026-08-01",
    type: "expense",
    category_id: null,
    description: `Item ${id}`,
    created_at: "2026-08-01T10:00:00",
    updated_at: null,
    ...overrides,
  };
}

const noop = vi.fn();

describe("TransactionList", () => {
  it("renders uncategorised transactions (category_id null)", () => {
    render(
      <TransactionList
        transactions={[tx(1, { amount: 42.5 })]}
        categories={[]}
        loading={false}
        error={null}
        onEdit={noop}
        onDelete={noop}
      />
    );

    expect(screen.getAllByText("$42.50").length).toBeGreaterThan(0);
  });

  it("shows the server total and reveals more rows on demand", async () => {
    const rows = Array.from({ length: LIST_PAGE_SIZE + 10 }, (_, i) => tx(i + 1));

    render(
      <TransactionList
        transactions={rows}
        total={rows.length}
        categories={[]}
        loading={false}
        error={null}
        onEdit={noop}
        onDelete={noop}
      />
    );

    expect(
      screen.getByText(`Showing ${LIST_PAGE_SIZE} of ${rows.length} transactions`)
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Show more" }));

    expect(
      screen.getByText(`Showing ${rows.length} of ${rows.length} transactions`)
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
  });
});
