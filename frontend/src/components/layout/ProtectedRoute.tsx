import { Navigate, Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import CurrentUserProvider from "../../context/CurrentUserProvider";

/**
 * Wraps protected routes.
 * Renders the top Navbar followed by child routes via <Outlet /> when an
 * access_token is present in localStorage; otherwise redirects to /login.
 * Wraps everything in CurrentUserProvider so pages can read the profile
 * (name, currency, timezone) loaded from GET /users/me.
 *
 * Requirements: 4.1 — Navbar appears on all authenticated pages.
 */
export default function ProtectedRoute() {
  const token = localStorage.getItem("access_token");
  const isAuthenticated = token !== null && token.length > 0;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <CurrentUserProvider>
      <Navbar />
      <Outlet />
    </CurrentUserProvider>
  );
}
