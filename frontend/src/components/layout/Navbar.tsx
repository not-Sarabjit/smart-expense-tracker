import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useCurrentUser } from "../../hooks/useCurrentUser";
import { applyTheme } from "../../utils/theme";

/**
 * Top navigation bar rendered on all authenticated pages.
 *
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11
 */
export default function Navbar() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  // Display name from GET /users/me — empty until the profile loads (Req 4.2)
  const { user } = useCurrentUser();
  const displayName = user ? `${user.first_name} ${user.last_name ?? ""}`.trim() : "";

  // Hamburger menu state for mobile (Req 4.10, 4.11)
  const [menuOpen, setMenuOpen] = useState(false);

  // Dark-mode state — initialised from current <html> class (Req 4.9)
  const [isDark, setIsDark] = useState(
    () => document.documentElement.classList.contains("dark")
  );

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function handleThemeToggle() {
    const next = isDark ? "light" : "dark";
    applyTheme(next); // Req 4.7 / 4.8: toggles class + persists to localStorage
    setIsDark(!isDark);
  }

  // Sun icon (shown in dark mode to switch back to light)
  const SunIcon = (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );

  // Moon icon (shown in light mode to switch to dark)
  const MoonIcon = (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );

  return (
    <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand / user name */}
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-800 dark:text-gray-100 text-sm sm:text-base">
              {displayName || "Smart Expense Tracker"}
            </span>
          </div>

          {/* Desktop nav links + controls (Req 4.3, 4.4, 4.5, 4.6) */}
          <div className="hidden md:flex items-center gap-4">
            <Link
              to="/dashboard"
              className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium text-sm transition-colors"
            >
              Dashboard
            </Link>
            <Link
              to="/categories"
              className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium text-sm transition-colors"
            >
              Categories
            </Link>
            <Link
              to="/settings"
              className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium text-sm transition-colors"
            >
              Settings
            </Link>

            {/* Dark / light mode toggle (Req 4.6, 4.7, 4.8) */}
            <button
              onClick={handleThemeToggle}
              className="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? SunIcon : MoonIcon}
            </button>

            {/* Logout (Req 4.5) */}
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 text-sm font-medium rounded-md bg-indigo-600 text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 transition-colors"
            >
              Logout
            </button>
          </div>

          {/* Mobile: hamburger button (Req 4.10, 4.11) */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMenuOpen((prev) => !prev)}
              className="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label="Toggle menu"
              aria-expanded={menuOpen}
            >
              {/* Three horizontal lines — hamburger icon */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                {menuOpen ? (
                  // X icon when menu is open
                  <>
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </>
                ) : (
                  // Hamburger lines
                  <>
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="18" x2="21" y2="18" />
                  </>
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile dropdown menu (Req 4.10, 4.11) */}
      {menuOpen && (
        <div className="md:hidden border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 flex flex-col gap-3">
          <Link
            to="/dashboard"
            className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium text-sm"
            onClick={() => setMenuOpen(false)}
          >
            Dashboard
          </Link>
          <Link
            to="/categories"
            className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium text-sm"
            onClick={() => setMenuOpen(false)}
          >
            Categories
          </Link>
          <Link
            to="/settings"
            className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium text-sm"
            onClick={() => setMenuOpen(false)}
          >
            Settings
          </Link>

          {/* Dark / light mode toggle in mobile menu */}
          <button
            onClick={handleThemeToggle}
            className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400"
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDark ? SunIcon : MoonIcon}
            <span>{isDark ? "Light mode" : "Dark mode"}</span>
          </button>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="text-left px-3 py-1.5 text-sm font-medium rounded-md bg-indigo-600 text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 transition-colors w-full"
          >
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
