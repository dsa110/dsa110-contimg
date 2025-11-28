import React from "react";
import { createRoot } from "react-dom/client";

/**
 * Main entry point for the DSA-110 Pipeline UI.
 * This is a minimal bootstrap; full application components will be added as development continues.
 */
const App: React.FC = () => {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "20px" }}>
      <h1>DSA-110 Pipeline UI</h1>
      <p>Frontend is running. Connect to the backend API to see data.</p>
    </div>
  );
};

const container = document.getElementById("root");
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
