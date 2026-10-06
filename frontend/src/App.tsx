import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import CategoriesPage from "./pages/CategoriesPage";
import SettingsPage from "./pages/SettingsPage";
import ChatPage from "./pages/ChatPage";
import ProtectedRoute from "./components/layout/ProtectedRoute";

/**
 * Renders /login but redirects to /dashboard when already authenticated.
 */
function LoginRoute() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated()) {
    return <Navigate to="/dashboard" replace />;
  }
  return <AuthPage />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public route — inverse guard redirects authenticated users away */}
        <Route path="/login" element={<LoginRoute />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:conversationId" element={<ChatPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Catch-all: redirect to /dashboard (ProtectedRoute handles auth check) */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
