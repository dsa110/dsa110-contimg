import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ServiceStatusPanel } from "./ServiceStatusPanel";

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

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
    // Mock successful fetch by default
    mockFetch.mockResolvedValue({ ok: true, type: "basic" });
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
      expect(screen.getByText("Vite Dev Server")).toBeInTheDocument();
      expect(screen.getByText("Grafana")).toBeInTheDocument();
      expect(screen.getByText("Redis")).toBeInTheDocument();
      expect(screen.getByText("FastAPI Backend")).toBeInTheDocument();
    });

    it("shows port numbers", async () => {
      render(<ServiceStatusPanel />);
      expect(screen.getByText("3000")).toBeInTheDocument();
      expect(screen.getByText("8000")).toBeInTheDocument();
    });

    it("shows service descriptions", async () => {
      render(<ServiceStatusPanel />);
      expect(screen.getByText(/frontend development server/i)).toBeInTheDocument();
    });
  });

  describe("status checking", () => {
    it("shows checking state initially", () => {
      mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
      render(<ServiceStatusPanel />);
      expect(screen.getAllByText(/checking/i).length).toBeGreaterThan(0);
    });

    it("shows running status when service responds", async () => {
      mockFetch.mockResolvedValue({ ok: true, type: "basic" });
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getAllByText(/running/i).length).toBeGreaterThan(0);
      });
    });

    it("shows stopped status when service fails", async () => {
      mockFetch.mockRejectedValue(new Error("Connection refused"));
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getAllByText(/stopped/i).length).toBeGreaterThan(0);
      });
    });
  });

  describe("refresh button", () => {
    it("renders refresh button", async () => {
      render(<ServiceStatusPanel />);
      // Wait for component to fully render including effects
      await waitFor(() => {
        const button = screen.queryByRole("button", { name: /refresh|checking/i });
        expect(button).toBeInTheDocument();
      });
    });

    it("triggers service check on click", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      mockFetch.mockClear();
      await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });

    it("shows checking state while refreshing", async () => {
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
      await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

      expect(screen.getByRole("button", { name: /checking/i })).toBeDisabled();
    });
  });

  describe("auto-refresh", () => {
    it("refreshes every 30 seconds", async () => {
      render(<ServiceStatusPanel />);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const initialCallCount = mockFetch.mock.calls.length;

      // Advance time by 30 seconds
      vi.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(mockFetch.mock.calls.length).toBeGreaterThan(initialCallCount);
      });
    });
  });

  describe("running count", () => {
    it("shows count of running services", async () => {
      mockFetch.mockResolvedValue({ ok: true, type: "basic" });
      render(<ServiceStatusPanel />);
      await waitFor(() => {
        expect(screen.getByText(/\d+\/\d+ services running/)).toBeInTheDocument();
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
});
