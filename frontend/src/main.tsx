import React from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { QueryProvider } from "./lib/queryClient";
import { AppErrorBoundary } from "./components/errors";
import { logger } from "./utils/logger";
import "./index.css";

/**
 * Main entry point for the DSA-110 Pipeline UI.
 *
 * Architecture:
 * - AppErrorBoundary: Global error boundary for unhandled errors
 * - QueryProvider: TanStack Query for server state management
 * - RouterProvider: React Router v6 for client-side routing
 * - Zustand stores: Imported directly where needed (no provider required)
 */

const container = document.getElementById("root");
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <AppErrorBoundary
        onError={(error, errorInfo) => {
          logger.error("Global error boundary caught error", error);
          logger.debug("Error info", { componentStack: errorInfo.componentStack });
        }}
      >
        <QueryProvider>
          <RouterProvider router={router} />
        </QueryProvider>
      </AppErrorBoundary>
    </React.StrictMode>
  );
}
