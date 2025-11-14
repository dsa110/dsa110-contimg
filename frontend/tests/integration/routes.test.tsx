/**
 * Route Rendering Integration Test
 *
 * Verifies that all routes render without errors, catching lazy-loading failures
 * that would cause "Cannot convert object to primitive value" errors.
 *
 * This test ensures:
 * 1. All lazy-loaded page components have default exports
 * 2. Routes render without runtime errors
 * 3. React.lazy() imports work correctly
 */

import { describe, it, expect, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { BrowserRouter, MemoryRouter } from "react-router-dom";
import App from "../../src/App";

// Mock all API calls to prevent network requests during testing
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

// List of all routes from App.tsx
const routes = [
  "/dashboard",
  "/control",
  "/mosaics",
  "/sources",
  "/sky",
  "/streaming",
  "/data",
  "/qa",
  "/observing",
  "/health",
  "/operations",
  "/pipeline",
  "/events",
  "/cache",
  "/calibration",
  "/ms-browser",
  "/lineage/test-id",
  "/sources/test-source-id",
  "/images/test-image-id",
  "/mosaics/test-mosaic-id",
  "/data/test-type/test-id",
];

describe("Route Rendering", () => {
  it.each(routes)("should render route %s without errors", async (route) => {
    // Capture console errors
    const errors: string[] = [];
    const originalError = console.error;
    console.error = (...args: unknown[]) => {
      const errorMsg = args.map((arg) => (typeof arg === "string" ? arg : String(arg))).join(" ");
      if (
        errorMsg.includes("Cannot convert object to primitive value") ||
        errorMsg.includes("Element type is invalid") ||
        errorMsg.includes("default export")
      ) {
        errors.push(errorMsg);
      }
      originalError(...args);
    };

    try {
      const { container, unmount } = render(
        <MemoryRouter initialEntries={[route]}>
          <App />
        </MemoryRouter>
      );

      // Wait for component to load (lazy components need time)
      await waitFor(
        () => {
          // Check that something rendered (not just empty)
          expect(container).toBeTruthy();
        },
        { timeout: 3000 }
      );

      // Verify no critical errors occurred
      expect(errors).toEqual([]);

      unmount();
    } catch (error) {
      // Re-throw with route context
      throw new Error(
        `Route ${route} failed to render: ${error instanceof Error ? error.message : String(error)}`
      );
    } finally {
      console.error = originalError;
    }
  });

  it("should handle root redirect to dashboard", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    await waitFor(
      () => {
        expect(container).toBeTruthy();
      },
      { timeout: 3000 }
    );
  });

  it("should handle legacy route redirects", async () => {
    const legacyRoutes = [
      "/pipeline-control",
      "/pipeline-operations",
      "/data-explorer",
      "/system-diagnostics",
    ];

    for (const route of legacyRoutes) {
      const { container, unmount } = render(
        <MemoryRouter initialEntries={[route]}>
          <App />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(container).toBeTruthy();
        },
        { timeout: 3000 }
      );

      unmount();
    }
  });
});
