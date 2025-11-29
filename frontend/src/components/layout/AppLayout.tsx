import React from "react";
import { Outlet, Link, useLocation } from "react-router-dom";

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
    <div
      className="app-layout"
      style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}
    >
      {/* Header */}
      <header
        style={{
          backgroundColor: "#1a1a2e",
          color: "white",
          padding: "12px 20px",
          display: "flex",
          alignItems: "center",
          gap: "24px",
        }}
      >
        <Link
          to="/"
          style={{ color: "white", textDecoration: "none", fontWeight: "bold", fontSize: "1.2rem" }}
        >
          DSA-110 Pipeline
        </Link>
        <nav style={{ display: "flex", gap: "16px" }}>
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              style={{
                color: isActive(item.path) ? "#4fc3f7" : "#ccc",
                textDecoration: "none",
                padding: "4px 8px",
                borderBottom: isActive(item.path) ? "2px solid #4fc3f7" : "2px solid transparent",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main style={{ flex: 1, padding: "20px", backgroundColor: "#f5f5f5" }}>
        <Outlet />
      </main>

      {/* Footer */}
      <footer
        style={{
          backgroundColor: "#1a1a2e",
          color: "#888",
          padding: "12px 20px",
          textAlign: "center",
          fontSize: "0.85rem",
        }}
      >
        DSA-110 Continuum Imaging Pipeline • Deep Synoptic Array
      </footer>
    </div>
  );
};

export default AppLayout;
