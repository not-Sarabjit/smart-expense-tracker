import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("./client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

import apiClient from "./client";
import {
  getTransactions,
  getAllTransactions,
  getSummary,
  createTransaction,
  MAX_PAGE_SIZE,
} from "./transactions";
import type { TransactionResponse } from "../types";

const get = apiClient.get as unknown as ReturnType<typeof vi.fn>;
const post = apiClient.post as unknown as ReturnType<typeof vi.fn>;

function apiTx(id: number, amount: string): TransactionResponse {
  return {
    id,
    amount,
    date: "2026-08-01",
    type: "expense",
    category_id: null,
    description: null,
    created_at: "2026-08-01T10:00:00",
    updated_at: null,
  };
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("getTransactions", () => {
  it("converts Decimal-string amounts to numbers and reads X-Total-Count", async () => {
    get.mockResolvedValue({
      data: [apiTx(1, "42.50"), apiTx(2, "0.10")],
      headers: { "x-total-count": "120" },
    });

    const page = await getTransactions({ limit: 2, offset: 0 });

    expect(page.items.map((t) => t.amount)).toEqual([42.5, 0.1]);
    expect(typeof page.items[0].amount).toBe("number");
    expect(page.total).toBe(120);
    expect(get).toHaveBeenCalledWith("/transactions", { params: { limit: 2, offset: 0 } });
  });

  it("falls back to the page length when the header is missing", async () => {
    get.mockResolvedValue({ data: [apiTx(1, "1.00")], headers: {} });

    expect((await getTransactions()).total).toBe(1);
  });
});

describe("getAllTransactions", () => {
  it("pages with limit/offset until X-Total-Count rows are loaded", async () => {
    const total = MAX_PAGE_SIZE + 5;
    get.mockImplementation((_url: string, { params }: { params: { offset: number; limit: number } }) => {
      const count = Math.min(params.limit, total - params.offset);
      const data = Array.from({ length: count }, (_, i) => apiTx(params.offset + i, "1.00"));
      return Promise.resolve({ data, headers: { "x-total-count": String(total) } });
    });

    const page = await getAllTransactions({ start_date: "2026-08-01" });

    expect(page.items).toHaveLength(total);
    expect(page.total).toBe(total);
    expect(get).toHaveBeenCalledTimes(2);
    expect(get.mock.calls[1][1].params).toEqual({
      start_date: "2026-08-01",
      limit: MAX_PAGE_SIZE,
      offset: MAX_PAGE_SIZE,
    });
  });
});

describe("getSummary", () => {
  it("returns the backend's income/expense/net keys as numbers", async () => {
    get.mockResolvedValue({ data: { income: 100.25, expense: "75.00", net: 25.25 } });

    expect(await getSummary(2026, 7)).toEqual({ income: 100.25, expense: 75, net: 25.25 });
  });
});

describe("createTransaction", () => {
  it("normalises the created transaction", async () => {
    post.mockResolvedValue({ data: apiTx(9, "12.30") });

    const tx = await createTransaction({
      amount: 12.3,
      date: "2026-08-01",
      type: "expense",
      category_id: null,
    });

    expect(tx.amount).toBe(12.3);
  });
});
