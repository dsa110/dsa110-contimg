import React from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { QueryProvider } from "./lib/queryClient";

/**
 * Main entry point for the DSA-110 Pipeline UI.
 *
 * Architecture:
 * - QueryProvider: TanStack Query for server state management
 * - RouterProvider: React Router v6 for client-side routing
 * - Zustand stores: Imported directly where needed (no provider required)
 */

const container = document.getElementById("root");
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <QueryProvider>
        <RouterProvider router={router} />
      </QueryProvider>
    </React.StrictMode>
  );
}
