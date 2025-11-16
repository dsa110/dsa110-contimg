// Initialize patches BEFORE any other code loads
// This ensures custom element guard and JS9 setTimeout patcher are active
// before third-party libraries register custom elements or use setTimeout
import "./utils/initCustomElementGuard";
import "./utils/js9/initPatcher";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
