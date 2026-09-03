import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AuthPage from './AuthPage';

// We mock the auth API module so no real network calls are made.
vi.mock('../api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
}));

import * as authApi from '../api/auth';

function renderAuthPage(initialPath = '/login') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route path="/dashboard" element={<div>Dashboard</div>} />
      </Routes>
    </MemoryRouter>
  );
}

/** Click the form's submit button (type="submit"), not the tab button */
function clickSubmit() {
  const submitBtn = document.querySelector('button[type="submit"]') as HTMLButtonElement;
  fireEvent.click(submitBtn);
}

describe('AuthPage — Login mode', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders email and password fields by default', () => {
    renderAuthPage();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('shows validation errors when email is empty on submit', async () => {
    renderAuthPage();
    clickSubmit();
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(authApi.login).not.toHaveBeenCalled();
  });

  it('shows validation errors when password is empty on submit', async () => {
    renderAuthPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com');
    clickSubmit();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
    expect(authApi.login).not.toHaveBeenCalled();
  });

  it('does not call the API when both fields are empty', async () => {
    renderAuthPage();
    clickSubmit();
    await waitFor(() => {
      expect(authApi.login).not.toHaveBeenCalled();
    });
  });

  it('calls login API with correct credentials and navigates to /dashboard on success', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'token-xyz' });

    renderAuthPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'secret');
    clickSubmit();

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith('user@example.com', 'secret');
    });
    expect(await screen.findByText('Dashboard')).toBeInTheDocument();
  });

  it('displays API error message below the submit button on login failure', async () => {
    const err = {
      isAxiosError: true,
      response: { data: { detail: 'Invalid credentials.' }, status: 401 },
    };
    vi.mocked(authApi.login).mockRejectedValue(err);

    renderAuthPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'bad@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpass');
    clickSubmit();

    expect(await screen.findByText('Invalid credentials.')).toBeInTheDocument();
  });
});

describe('AuthPage — Register mode', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  function switchToRegister() {
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }));
  }

  it('shows first_name, last_name, email, and password fields in register mode', () => {
    renderAuthPage();
    switchToRegister();
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('shows validation errors for all empty fields on submit', async () => {
    renderAuthPage();
    switchToRegister();
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    expect(await screen.findByText(/first name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/last name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    expect(authApi.register).not.toHaveBeenCalled();
  });

  it('does not call API when any required field is empty (whitespace-only)', async () => {
    renderAuthPage();
    switchToRegister();
    await userEvent.type(screen.getByLabelText(/first name/i), '   ');
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(authApi.register).not.toHaveBeenCalled();
    });
  });

  it('calls register then auto-login and navigates to /dashboard on success', async () => {
    const user = { id: 1, email: 'new@example.com', first_name: 'Alice', last_name: 'Smith', created_at: '' };
    vi.mocked(authApi.register).mockResolvedValue(user);
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'new-token' });

    renderAuthPage();
    switchToRegister();
    await userEvent.type(screen.getByLabelText(/first name/i), 'Alice');
    await userEvent.type(screen.getByLabelText(/last name/i), 'Smith');
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(authApi.register).toHaveBeenCalledWith({
        first_name: 'Alice',
        last_name: 'Smith',
        email: 'new@example.com',
        password: 'password123',
      });
    });
    expect(await screen.findByText('Dashboard')).toBeInTheDocument();
  });
});
