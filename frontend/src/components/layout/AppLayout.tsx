import React from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { ConnectionStatus } from "../common/ConnectionStatus";
import { useNetworkNotifications } from "../../hooks/useNetworkNotifications";
import { NAV_ITEMS, ROUTES, isRouteActive } from "../../constants/routes";
import { UserMenu } from "../common/UserMenu";
import { useAuth } from "../../hooks/useAuth";

/**
 * Main application layout with navigation and content area.
 * Uses GitHub-inspired dark theme optimized for astronomers.
 */
const AppLayout: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  // Enable network status notifications (shows toasts on connect/disconnect)
  useNetworkNotifications();

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ backgroundColor: "var(--color-bg-default)" }}
    >
      {/* Connection status banner (appears when offline/degraded) */}
      <ConnectionStatus showDetails />

      {/* Header - Dark surface */}
      <header
        className="px-6 py-3 flex items-center gap-8 shadow-md"
        style={{
          backgroundColor: "var(--color-bg-paper)",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <Link
          to={ROUTES.HOME}
          className="no-underline font-bold text-xl transition-colors"
          style={{ color: "var(--color-primary)" }}
        >
          DSA-110 / Continuum
        </Link>
        <nav className="flex gap-1 flex-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors"
              style={{
                backgroundColor: isRouteActive(location.pathname, item.path)
                  ? "var(--color-bg-surface)"
                  : "transparent",
                color: isRouteActive(location.pathname, item.path)
                  ? "var(--color-primary)"
                  : "var(--color-text-secondary)",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* User menu or login link */}
        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <UserMenu />
          ) : (
            <Link
              to="/login"
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors"
              style={{
                backgroundColor: "var(--color-primary)",
                color: "white",
              }}
            >
              Sign in
            </Link>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6">
        <Outlet />
      </main>

      {/* Footer - Dark surface */}
      <footer
        className="px-6 py-3 text-center text-sm"
        style={{
          backgroundColor: "var(--color-bg-paper)",
          color: "var(--color-text-secondary)",
          borderTop: "1px solid var(--color-border)",
        }}
      >
        DSA-110 Continuum Imaging Pipeline • Deep Synoptic Array
      </footer>
    </div>
  );
};

export default AppLayout;
