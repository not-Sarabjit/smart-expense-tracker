import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';

// Helper: renders a MemoryRouter pointing at `initialPath` with the full
// route tree: protected group + /login public route.
function renderWithRouter(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard Page</div>} />
          <Route path="/categories" element={<div>Categories Page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('redirects unauthenticated user from /dashboard to /login', () => {
    renderWithRouter('/dashboard');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard Page')).not.toBeInTheDocument();
  });

  it('redirects unauthenticated user from /categories to /login', () => {
    renderWithRouter('/categories');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Categories Page')).not.toBeInTheDocument();
  });

  it('renders the protected route when access_token is present', () => {
    localStorage.setItem('access_token', 'valid-token');
    renderWithRouter('/dashboard');
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('renders categories page when authenticated', () => {
    localStorage.setItem('access_token', 'valid-token');
    renderWithRouter('/categories');
    expect(screen.getByText('Categories Page')).toBeInTheDocument();
  });

  it('redirects when token is empty string', () => {
    localStorage.setItem('access_token', '');
    renderWithRouter('/dashboard');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });
});
