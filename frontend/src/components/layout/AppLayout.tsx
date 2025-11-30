import React from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { ConnectionStatus } from "../common/ConnectionStatus";
import { useNetworkNotifications } from "../../hooks/useNetworkNotifications";
import { NAV_ITEMS, ROUTES, isRouteActive } from "../../constants/routes";

/**
 * Main application layout with navigation and content area.
 */
const AppLayout: React.FC = () => {
  const location = useLocation();

  // Enable network status notifications (shows toasts on connect/disconnect)
  useNetworkNotifications();

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Connection status banner (appears when offline/degraded) */}
      <ConnectionStatus showDetails />

      {/* Header */}
      <header className="bg-slate-900 text-white px-6 py-3 flex items-center gap-8 shadow-md">
        <Link
          to={ROUTES.HOME}
          className="text-white no-underline font-bold text-xl hover:text-cyan-300 transition-colors"
        >
          DSA-110 Pipeline
        </Link>
        <nav className="flex gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                isRouteActive(location.pathname, item.path)
                  ? "bg-slate-700 text-cyan-300"
                  : "text-gray-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-gray-400 px-6 py-3 text-center text-sm">
        DSA-110 Continuum Imaging Pipeline :bullet: Deep Synoptic Array
      </footer>
    </div>
  );
};

export default AppLayout;
