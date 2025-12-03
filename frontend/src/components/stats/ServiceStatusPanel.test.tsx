import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ServiceStatusPanel } from "./ServiceStatusPanel";
import * as healthChecker from "../../utils/serviceHealthChecker";

// Hoisted mock for ServiceHealthChecker class
const mockChecker = vi.hoisted(() => ({
  checkAllServices: vi.fn(),
  abort: vi.fn(),
  reset: vi.fn(),
}));

// Mock the health checker module
vi.mock("../../utils/serviceHealthChecker", async (importOriginal) => {
  const actual = await importOriginal<typeof healthChecker>();
  return {
    ...actual,
    ServiceHealthChecker: class MockServiceHealthChecker {
      checkAllServices = mockChecker.checkAllServices;
      abort = mockChecker.abort;
      reset = mockChecker.reset;
    },
  };
});

// Create mock result for health checker
const createMockHealthResult = (overrides = {}) => ({
  results: [
    {
      name: "Vite Dev Server",
      port: 3000,
      description: "Frontend development server with HMR",
      status: "running",
      responseTime: 50,
      lastChecked: new Date(),
      source: "backend-api",
      failureCount: 0,
    },
    {
      name: "Grafana",
      port: 3030,
      description: "Metrics visualization dashboards",
      status: "running",
      responseTime: 100,
      lastChecked: new Date(),
      source: "backend-api",
      failureCount: 0,
    },
    {
      name: "Redis",
      port: 6379,
      description: "API response caching",
      status: "running",
      responseTime: 10,
      lastChecked: new Date(),
      source: "backend-api",
      failureCount: 0,
    },
    {
      name: "FastAPI Backend",
      port: 8000,
      description: "REST API for pipeline data",
      status: "running",
      responseTime: 30,
      lastChecked: new Date(),
      source: "backend-api",
      failureCount: 0,
    },
    {
      name: "MkDocs",
      port: 8001,
      description: "Documentation server (dev only)",
      status: "stopped",
      responseTime: undefined,
      lastChecked: new Date(),
      error: "Connection refused",
      source: "backend-api",
      failureCount: 2,
    },
    {
      name: "Prometheus",
      port: 9090,
      description: "Metrics collection and storage",
      status: "running",
      responseTime: 20,
      lastChecked: new Date(),
      source: "backend-api",
      failureCount: 0,
    },
  ],
  apiAvailable: true,
  diagnostics: {
    backendAttempts: 1,
    backendError: null,
    fallbackUsed: false,
    individualProbes: [],
  },
  ...overrides,
});

// Suppress console.error for act() warnings in tests with intentionally pending promises
const originalError = console.error;
beforeEach(() => {
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === "string" && args[0].includes("not wrapped in act")) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterEach(() => {
  console.error = originalError;
});

describe("ServiceStatusPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    // Set up default mock implementation
    mockChecker.checkAllServices.mockResolvedValue(createMockHealthResult());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("rendering", () => {
    it("renders panel title", async () => {
      render(<ServiceStatusPanel />);
      expect(screen.getByText("Service Status")).toBeInTheDocument();
    });

    it("shows service list", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getByText("Vite Dev Server")).toBeInTheDocument();
        expect(screen.getByText("Grafana")).toBeInTheDocument();
        expect(screen.getByText("Redis")).toBeInTheDocument();
        expect(screen.getByText("FastAPI Backend")).toBeInTheDocument();
      });
    });

    it("shows port numbers", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getByText("3000")).toBeInTheDocument();
        expect(screen.getByText("8000")).toBeInTheDocument();
      });
    });

    it("shows service descriptions", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(
          screen.getByText(/frontend development server/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe("status checking", () => {
    it("shows checking state initially", () => {
      mockChecker.checkAllServices.mockImplementation(
        () => new Promise(() => {})
      ); // Never resolves
      render(<ServiceStatusPanel />);
      expect(screen.getAllByText(/checking/i).length).toBeGreaterThan(0);
    });

    it("shows running status when services respond", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getAllByText(/running/i).length).toBeGreaterThan(0);
      });
    });

    it("shows stopped status when service fails", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getAllByText(/stopped/i).length).toBeGreaterThan(0);
      });
    });

    it("shows API connected indicator when backend is available", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getByText(/backend api connected/i)).toBeInTheDocument();
      });
    });
  });

  describe("fallback mode", () => {
    it("shows fallback banner when backend is unavailable", async () => {
      mockChecker.checkAllServices.mockResolvedValue({
        results: healthChecker.DEFAULT_SERVICES.map((s) => ({
          ...s,
          status: "unknown" as const,
          lastChecked: new Date(),
          source: "fallback" as const,
          failureCount: 1,
        })),
        apiAvailable: false,
        diagnostics: {
          backendAttempts: 3,
          backendError: "Connection refused",
          fallbackUsed: true,
          individualProbes: [
            {
              service: "Vite Dev Server",
              success: true,
              source: "client-probe",
            },
            {
              service: "Redis",
              success: false,
              source: "fallback",
              error: "Cannot probe from browser",
            },
          ],
        },
      });

      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(
          screen.getByText(/backend api unavailable/i)
        ).toBeInTheDocument();
      });
    });

    it("shows diagnostics details when backend fails", async () => {
      mockChecker.checkAllServices.mockResolvedValue({
        results: healthChecker.DEFAULT_SERVICES.map((s) => ({
          ...s,
          status: "unknown" as const,
          lastChecked: new Date(),
          source: "fallback" as const,
          failureCount: 1,
        })),
        apiAvailable: false,
        diagnostics: {
          backendAttempts: 3,
          backendError: "Connection refused",
          fallbackUsed: true,
          individualProbes: [],
        },
      });

      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getByText(/3 backend attempts/i)).toBeInTheDocument();
      });
    });
  });

  describe("failure tracking", () => {
    it("shows failure count badge for services with consecutive failures", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        // MkDocs has failureCount: 2 in mock data
        expect(screen.getByText("×2")).toBeInTheDocument();
      });
    });
  });

  describe("source badges", () => {
    it("shows source badge for API-sourced results", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getAllByText("API").length).toBeGreaterThan(0);
      });
    });
  });

  describe("refresh button", () => {
    it("renders refresh button", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        const button = screen.queryByRole("button", {
          name: /refresh|checking/i,
        });
        expect(button).toBeInTheDocument();
      });
    });

    it("triggers service check on click", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(mockChecker.checkAllServices).toHaveBeenCalled();
      });

      mockChecker.checkAllServices.mockClear();
      await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

      await waitFor(() => {
        expect(mockChecker.checkAllServices).toHaveBeenCalled();
      });
    });

    it("shows checking state while refreshing", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(mockChecker.checkAllServices).toHaveBeenCalled();
      });

      mockChecker.checkAllServices.mockImplementation(
        () => new Promise(() => {})
      ); // Never resolves
      await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

      expect(screen.getByRole("button", { name: /checking/i })).toBeDisabled();
    });
  });

  describe("auto-refresh", () => {
    it("refreshes every 30 seconds", async () => {
      render(<ServiceStatusPanel />);

      await waitFor(() => {
        expect(mockChecker.checkAllServices).toHaveBeenCalled();
      });

      const initialCallCount = mockChecker.checkAllServices.mock.calls.length;

      // Advance time by 30 seconds
      vi.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(mockChecker.checkAllServices.mock.calls.length).toBeGreaterThan(
          initialCallCount
        );
      });
    });
  });

  describe("running count", () => {
    it("shows count of running services", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(
          screen.getByText(/\d+\/\d+ services running/)
        ).toBeInTheDocument();
      });
    });
  });

  describe("last checked time", () => {
    it("shows last checked timestamp", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getByText(/last checked:/i)).toBeInTheDocument();
      });
    });
  });

  describe("cleanup", () => {
    it("aborts health checker on unmount", async () => {
      const { unmount } = render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(mockChecker.checkAllServices).toHaveBeenCalled();
      });
      unmount();
      expect(mockChecker.abort).toHaveBeenCalled();
    });
  });
});
