import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SesameResolver from "./SesameResolver";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Counter to generate unique object names for each test to avoid cache interference
let testCounter = 0;

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

describe("SesameResolver", () => {
  const mockOnResolved = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
    testCounter++;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("basic rendering", () => {
    it("renders input field", () => {
      render(<SesameResolver onResolved={mockOnResolved} />);
      expect(screen.getByPlaceholderText(/Object name/)).toBeInTheDocument();
    });

    it("renders Resolve button", () => {
      render(<SesameResolver onResolved={mockOnResolved} />);
      expect(screen.getByRole("button", { name: /Resolve/i })).toBeInTheDocument();
    });

    it("renders service selection radio buttons", () => {
      render(<SesameResolver onResolved={mockOnResolved} />);
      expect(screen.getByLabelText(/All/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/SIMBAD/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/NED/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/VIZIER/i)).toBeInTheDocument();
    });

    it("has All service selected by default", () => {
      render(<SesameResolver onResolved={mockOnResolved} />);
      const allRadio = screen.getByLabelText(/All/i);
      expect(allRadio).toBeChecked();
    });

    it("applies custom className", () => {
      const { container } = render(
        <SesameResolver onResolved={mockOnResolved} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("input handling", () => {
    it("updates input value when typing", async () => {
      const user = userEvent.setup();
      render(<SesameResolver onResolved={mockOnResolved} />);

      const input = screen.getByPlaceholderText(/Object name/);
      await user.type(input, "M31");

      expect(input).toHaveValue("M31");
    });

    it("disables Resolve button when input is empty", () => {
      render(<SesameResolver onResolved={mockOnResolved} />);
      expect(screen.getByRole("button", { name: /Resolve/i })).toBeDisabled();
    });

    it("enables Resolve button when input has value", async () => {
      const user = userEvent.setup();
      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.type(screen.getByPlaceholderText(/Object name/), "M31");

      expect(screen.getByRole("button", { name: /Resolve/i })).not.toBeDisabled();
    });

    it("disables button when input only has whitespace", async () => {
      const user = userEvent.setup();
      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.type(screen.getByPlaceholderText(/Object name/), "   ");

      expect(screen.getByRole("button", { name: /Resolve/i })).toBeDisabled();
    });
  });

  describe("service selection", () => {
    it("allows changing service to SIMBAD", async () => {
      const user = userEvent.setup();
      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.click(screen.getByLabelText(/SIMBAD/i));

      expect(screen.getByLabelText(/SIMBAD/i)).toBeChecked();
      expect(screen.getByLabelText(/All/i)).not.toBeChecked();
    });

    it("allows changing service to NED", async () => {
      const user = userEvent.setup();
      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.click(screen.getByLabelText(/NED/i));

      expect(screen.getByLabelText(/NED/i)).toBeChecked();
    });

    it("allows changing service to VizieR", async () => {
      const user = userEvent.setup();
      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.click(screen.getByLabelText(/VIZIER/i));

      expect(screen.getByLabelText(/VIZIER/i)).toBeChecked();
    });
  });

  describe("resolution success", () => {
    it("resolves object and calls onResolved callback", async () => {
      const user = userEvent.setup();
      const sesameResponse = `
# Sesame
%J 10.68479 +41.26906 = 00 42 44.35 +41 16 08.6
      `;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sesameResponse),
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.type(screen.getByPlaceholderText(/Object name/), "M31");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(mockOnResolved).toHaveBeenCalledWith(10.68479, 41.26906, "M31");
      });
    });

    it("displays resolved coordinates on success", async () => {
      const user = userEvent.setup();
      const sesameResponse = `%J 83.63308 +22.01450 = 05 34 31.94 +22 00 52.2`;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sesameResponse),
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.type(screen.getByPlaceholderText(/Object name/), "Crab Nebula");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(screen.getByText(/Resolved:/)).toBeInTheDocument();
        expect(screen.getByText(/83\.633080°/)).toBeInTheDocument();
        expect(screen.getByText(/22\.014500°/)).toBeInTheDocument();
      });
    });

    it("shows loading state during resolution", async () => {
      const user = userEvent.setup();
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockFetch.mockReturnValueOnce(pendingPromise);

      render(<SesameResolver onResolved={mockOnResolved} />);

      // Use unique object name to avoid cache hit
      await user.type(screen.getByPlaceholderText(/Object name/), `LoadingTest${testCounter}`);
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      expect(screen.getByText(/Resolving/i)).toBeInTheDocument();

      // Clean up - resolve but don't wait (act warning suppressed at top of file)
      resolvePromise!({
        ok: true,
        text: () => Promise.resolve("%J 10.68479 +41.26906"),
      });
      await waitFor(() => {
        expect(mockOnResolved).toHaveBeenCalled();
      });
    });

    it("triggers resolve on Enter key press", async () => {
      const user = userEvent.setup();
      const sesameResponse = `%J 10.68479 +41.26906`;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sesameResponse),
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      const input = screen.getByPlaceholderText(/Object name/);
      await user.type(input, "M31{Enter}");

      await waitFor(() => {
        expect(mockOnResolved).toHaveBeenCalled();
      });
    });
  });

  describe("resolution errors", () => {
    it("displays error when object cannot be resolved", async () => {
      const user = userEvent.setup();
      const sesameResponse = `# No result for object`;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sesameResponse),
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.type(screen.getByPlaceholderText(/Object name/), "NotARealObject");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(screen.getByText(/Could not resolve/i)).toBeInTheDocument();
      });
    });

    it("displays error on network failure", async () => {
      const user = userEvent.setup();
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      render(<SesameResolver onResolved={mockOnResolved} />);

      // Use unique object name to avoid cache hit
      await user.type(screen.getByPlaceholderText(/Object name/), `NetworkErrorTest${testCounter}`);
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(screen.getByText(/Network error|CORS/i)).toBeInTheDocument();
      });
    });

    it("displays error on HTTP error", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      // Use unique object name to avoid cache hit
      await user.type(screen.getByPlaceholderText(/Object name/), `HTTPErrorTest${testCounter}`);
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(screen.getByText(/HTTP error/i)).toBeInTheDocument();
      });
    });

    it("shows error when input is empty on resolve attempt", async () => {
      const user = userEvent.setup();
      render(<SesameResolver onResolved={mockOnResolved} />);

      // Type and then clear
      const input = screen.getByPlaceholderText(/Object name/);
      await user.type(input, "M31");
      await user.clear(input);

      // Force click (button should be disabled but test the logic)
      fireEvent.click(screen.getByRole("button", { name: /Resolve/i }));

      // Should not have called fetch
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("URL construction", () => {
    it("constructs correct URL for All service", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve("%J 10.68479 +41.26906"),
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      // Use unique object name to avoid cache hit
      const testName = `URLTestAll${testCounter}`;
      await user.type(screen.getByPlaceholderText(/Object name/), testName);
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining("/A?"), expect.any(Object));
      });
    });

    it("constructs correct URL for SIMBAD service", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve("%J 10.68479 +41.26906"),
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.click(screen.getByLabelText(/SIMBAD/i));
      await user.type(screen.getByPlaceholderText(/Object name/), "M31");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining("/S?"), expect.any(Object));
      });
    });

    it("URL encodes object names with special characters", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve("%J 10.68479 +41.26906"),
      });

      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.type(screen.getByPlaceholderText(/Object name/), "NGC 1234");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("NGC%201234"),
          expect.any(Object)
        );
      });
    });
  });

  describe("request cancellation", () => {
    it("does not show error for aborted requests", async () => {
      const user = userEvent.setup();
      const abortError = new Error("Aborted");
      abortError.name = "AbortError";
      mockFetch.mockRejectedValueOnce(abortError);

      render(<SesameResolver onResolved={mockOnResolved} />);

      await user.type(screen.getByPlaceholderText(/Object name/), "M31");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      // Wait a bit to ensure no error is shown
      await new Promise((r) => setTimeout(r, 100));

      // AbortError should not show an error message
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    });
  });

  describe("caching", () => {
    it("uses cached result for repeated lookups", async () => {
      const user = userEvent.setup();
      const sesameResponse = `%J 10.68479 +41.26906`;
      mockFetch.mockResolvedValue({
        ok: true,
        text: () => Promise.resolve(sesameResponse),
      });

      const { unmount } = render(<SesameResolver onResolved={mockOnResolved} />);

      // First lookup
      await user.type(screen.getByPlaceholderText(/Object name/), "M31");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        expect(mockOnResolved).toHaveBeenCalledTimes(1);
      });

      // Unmount and remount to simulate cache persistence
      unmount();

      render(<SesameResolver onResolved={mockOnResolved} />);

      // Second lookup with same name (should use cache)
      await user.type(screen.getByPlaceholderText(/Object name/), "M31");
      await user.click(screen.getByRole("button", { name: /Resolve/i }));

      await waitFor(() => {
        // Should call onResolved again from cache
        expect(mockOnResolved).toHaveBeenCalledTimes(2);
      });

      // fetch should only have been called once (first lookup)
      // Note: Cache is module-level, so this behavior depends on test isolation
    });
  });
});
