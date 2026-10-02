import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SummaryCards } from "./SummaryCards";

describe("SummaryCards", () => {
  it("shows the totals from the backend's income/expense/net keys (bug B4)", () => {
    render(
      <SummaryCards
        summary={{ income: 3000, expense: 1250.5, net: 1749.5 }}
        loading={false}
        error={null}
      />
    );

    expect(screen.getByText("₹3,000.00")).toBeInTheDocument();
    expect(screen.getByText("₹1,250.50")).toBeInTheDocument();
    expect(screen.getByText("₹1,749.50")).toBeInTheDocument();
  });

  it("shows a negative net balance", () => {
    render(
      <SummaryCards summary={{ income: 10, expense: 25, net: -15 }} loading={false} error={null} />
    );

    expect(screen.getByText("-₹15.00")).toBeInTheDocument();
  });
});
