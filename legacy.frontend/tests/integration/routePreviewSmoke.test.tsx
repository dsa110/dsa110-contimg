/**
 * Route Preview Smoke Tests
 *
 * Ensures that the application renders when served under the /ui base path,
 * which matches how Vite preview and production deployments host the dashboard.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import App from "../../src/App";

vi.mock("../../src/api/queries", () => ({
  usePipelineStatus: () => ({
    data: null,
    isLoading: false,
    error: null,
  }),
  useSystemMetrics: () => ({
    data: null,
    isLoading: false,
    error: null,
  }),
}));

vi.mock("../../src/config/env", () => ({
  env: {
    VITE_API_URL: undefined,
    VITE_SENTRY_DSN: undefined,
    VITE_CARTA_FRONTEND_URL: undefined,
    VITE_CARTA_BACKEND_URL: undefined,
    PROD: true,
    DEV: false,
  },
}));

const previewRoutes = ["/ui/dashboard", "/ui/observing", "/ui/pipeline"];

describe("Route preview smoke", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
  });

  it.each(previewRoutes)("renders %s without crashing", async (route) => {
    const errors: string[] = [];
    const originalError = console.error;

    console.error = (...args: unknown[]) => {
      errors.push(args.map((arg) => (typeof arg === "string" ? arg : String(arg))).join(" "));
      originalError(...args);
    };

    try {
      window.history.replaceState({}, "", route);

      const { container, unmount } = render(<App />);

      await waitFor(() => {
        expect(container).toBeTruthy();
      });

      expect(errors).toEqual([]);
      unmount();
    } finally {
      console.error = originalError;
    }
  });
});
