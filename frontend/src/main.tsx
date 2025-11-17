// Initialize patches BEFORE any other code loads
// This ensures custom element guard and JS9 setTimeout patcher are active
// before third-party libraries register custom elements or use setTimeout
import "./utils/initCustomElementGuard";
import "./utils/js9/initPatcher";

// CRITICAL: Import React explicitly to ensure it's in the main bundle
// This ensures React is available before any lazy-loaded modules (like Plotly) load
import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Ensure React is available globally for libraries that may access it at module load time
// This prevents "Cannot set properties of undefined" errors
if (typeof window !== "undefined") {
  (window as any).React = React;
}
import "./index.css";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
