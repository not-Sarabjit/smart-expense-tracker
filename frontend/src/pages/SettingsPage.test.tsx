import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axios from "axios";
import { MemoryRouter } from "react-router-dom";

vi.mock("../api/users", () => ({ getMe: vi.fn(), updateMe: vi.fn() }));

import { getMe, updateMe } from "../api/users";
import CurrentUserProvider from "../context/CurrentUserProvider";
import Navbar from "../components/layout/Navbar";
import SettingsPage from "./SettingsPage";
import type { User } from "../types";

const mockedGetMe = vi.mocked(getMe);
const mockedUpdateMe = vi.mocked(updateMe);

const ADA: User = {
  id: 1,
  email: "ada@example.com",
  first_name: "Ada",
  last_name: "Lovelace",
  currency: "INR",
  timezone: "Asia/Kolkata",
  created_at: "2026-01-01T00:00:00",
};

function renderSettings() {
  return render(
    <MemoryRouter>
      <CurrentUserProvider>
        <Navbar />
        <SettingsPage />
      </CurrentUserProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  mockedGetMe.mockReset().mockResolvedValue(ADA);
  mockedUpdateMe.mockReset();
  localStorage.clear();
});

describe("SettingsPage", () => {
  it("loads the profile from GET /users/me (not localStorage)", async () => {
    localStorage.setItem("user_profile", JSON.stringify({ first_name: "Stale" }));

    renderSettings();

    expect(await screen.findByLabelText("Currency")).toHaveValue("INR");
    expect(screen.getByLabelText("Timezone")).toHaveValue("Asia/Kolkata");
    expect(screen.getByLabelText("First name")).toHaveValue("Ada");
    // Navbar name comes from the same profile
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.queryByText("Stale")).not.toBeInTheDocument();
  });

  it("sends only changed fields and shows the saved profile", async () => {
    mockedUpdateMe.mockResolvedValue({ ...ADA, currency: "USD", timezone: "UTC" });
    renderSettings();
    await screen.findByLabelText("Currency");

    await userEvent.selectOptions(screen.getByLabelText("Currency"), "USD");
    await userEvent.selectOptions(screen.getByLabelText("Timezone"), "UTC");
    await userEvent.click(screen.getByRole("button", { name: /save settings/i }));

    expect(mockedUpdateMe).toHaveBeenCalledWith({ currency: "USD", timezone: "UTC" });
    expect(await screen.findByText("Settings saved.")).toBeInTheDocument();
    expect(screen.getByLabelText("Currency")).toHaveValue("USD");
  });

  it("shows the server's validation message on failure", async () => {
    const err = new axios.AxiosError("Unprocessable");
    err.response = {
      status: 422,
      statusText: "Unprocessable Entity",
      data: { detail: [{ msg: "Value error, Timezone must be an IANA name" }] },
      headers: {},
      config: {} as never,
    };
    mockedUpdateMe.mockRejectedValue(err);
    renderSettings();
    await screen.findByLabelText("Currency");

    await userEvent.selectOptions(screen.getByLabelText("Currency"), "EUR");
    await userEvent.click(screen.getByRole("button", { name: /save settings/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Timezone must be an IANA name");
  });

  it("requires a first name", async () => {
    renderSettings();
    await screen.findByLabelText("First name");

    await userEvent.clear(screen.getByLabelText("First name"));
    await userEvent.click(screen.getByRole("button", { name: /save settings/i }));

    expect(screen.getByRole("alert")).toHaveTextContent("First name is required.");
    expect(mockedUpdateMe).not.toHaveBeenCalled();
  });

  it("shows an error when the profile cannot be loaded", async () => {
    mockedGetMe.mockRejectedValue(new Error("boom"));
    renderSettings();

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to load your profile.")
    );
  });
});
