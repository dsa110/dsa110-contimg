import React from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { ConnectionStatus } from "../common/ConnectionStatus";

/**
 * Main application layout with navigation and content area.
 */
const AppLayout: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Home" },
    { path: "/images", label: "Images" },
    { path: "/sources", label: "Sources" },
    { path: "/jobs", label: "Jobs" },
  ];

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Connection status banner (appears when offline/degraded) */}
      <ConnectionStatus showDetails />

      {/* Header */}
      <header className="bg-slate-900 text-white px-6 py-3 flex items-center gap-8 shadow-md">
        <Link
          to="/"
          className="text-white no-underline font-bold text-xl hover:text-cyan-300 transition-colors"
        >
          DSA-110 Pipeline
        </Link>
        <nav className="flex gap-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive(item.path)
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
