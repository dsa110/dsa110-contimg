import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import JobsListPage from "./JobsListPage";

// Mock the hooks
vi.mock("../hooks/useQueries", () => ({
  useJobs: vi.fn(),
}));

vi.mock("../stores/appStore", () => ({
  useSelectionStore: vi.fn((selector) => {
    const state = {
      selectedJobs: new Set<string>(),
      toggleJobSelection: vi.fn(),
      selectAllJobs: vi.fn(),
      clearJobSelection: vi.fn(),
    };
    return selector(state);
  }),
}));

import { useJobs } from "../hooks/useQueries";

const mockUseJobs = vi.mocked(useJobs);

describe("JobsListPage", () => {
  let queryClient: QueryClient;

  const mockJobs = [
    { run_id: "run-001", status: "completed", started_at: "2024-01-15T10:00:00Z" },
    { run_id: "run-002", status: "running", started_at: "2024-01-15T11:00:00Z" },
    { run_id: "run-003", status: "failed", started_at: "2024-01-15T09:00:00Z" },
    { run_id: "run-004", status: "pending", started_at: "2024-01-15T12:00:00Z" },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const renderPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <JobsListPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe("loading state", () => {
    it("shows loading spinner when loading", () => {
      mockUseJobs.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as ReturnType<typeof useJobs>);

      renderPage();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message when fetch fails", () => {
      mockUseJobs.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Failed to fetch"),
      } as ReturnType<typeof useJobs>);

      renderPage();
      expect(screen.getByText(/failed to load jobs/i)).toBeInTheDocument();
    });
  });

  describe("with data", () => {
    beforeEach(() => {
      mockUseJobs.mockReturnValue({
        data: mockJobs,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useJobs>);
    });

    it("renders page heading", () => {
      renderPage();
      expect(screen.getByRole("heading", { name: /jobs|pipeline/i })).toBeInTheDocument();
    });

    it("renders jobs in table", () => {
      renderPage();
      expect(screen.getByText("run-001")).toBeInTheDocument();
      expect(screen.getByText("run-002")).toBeInTheDocument();
      expect(screen.getByText("run-003")).toBeInTheDocument();
    });

    it("renders status badges", () => {
      renderPage();
      expect(screen.getByText("completed")).toBeInTheDocument();
      expect(screen.getByText("running")).toBeInTheDocument();
      expect(screen.getByText("failed")).toBeInTheDocument();
    });

    it("renders sortable table headers", () => {
      renderPage();
      expect(screen.getByRole("columnheader", { name: /run id/i })).toBeInTheDocument();
      expect(screen.getByRole("columnheader", { name: /status/i })).toBeInTheDocument();
    });

    it("renders job links", () => {
      renderPage();
      const link = screen.getByRole("link", { name: /run-001/i });
      expect(link).toHaveAttribute("href", "/jobs/run-001");
    });
  });

  describe("status badge styling", () => {
    beforeEach(() => {
      mockUseJobs.mockReturnValue({
        data: mockJobs,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useJobs>);
    });

    it("completed status has success styling", () => {
      renderPage();
      const completed = screen.getByText("completed");
      expect(completed).toHaveClass(/success|green/i);
    });

    it("failed status has error styling", () => {
      renderPage();
      const failed = screen.getByText("failed");
      expect(failed).toHaveClass(/error|red/i);
    });
  });

  describe("empty state", () => {
    it("shows message when no jobs", () => {
      mockUseJobs.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useJobs>);

      renderPage();
      expect(screen.getByText(/no jobs/i)).toBeInTheDocument();
    });
  });

  describe("selection and bulk actions", () => {
    beforeEach(() => {
      mockUseJobs.mockReturnValue({
        data: mockJobs,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useJobs>);
    });

    it("renders select all checkbox", () => {
      renderPage();
      const checkboxes = screen.getAllByRole("checkbox");
      expect(checkboxes.length).toBeGreaterThan(0);
    });

    it("renders row checkboxes", () => {
      renderPage();
      const checkboxes = screen.getAllByRole("checkbox");
      // Should have one for select all + one per row
      expect(checkboxes.length).toBe(mockJobs.length + 1);
    });
  });

  describe("sorting", () => {
    beforeEach(() => {
      mockUseJobs.mockReturnValue({
        data: mockJobs,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useJobs>);
    });

    it("clicking header triggers sort", async () => {
      const user = userEvent.setup();
      renderPage();

      const statusHeader = screen.getByRole("columnheader", { name: /status/i });
      await user.click(statusHeader);

      // Header should indicate sort direction
      expect(statusHeader).toHaveAttribute("aria-sort");
    });
  });

  describe("relative time", () => {
    beforeEach(() => {
      mockUseJobs.mockReturnValue({
        data: mockJobs,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useJobs>);
    });

    it("displays relative time for started_at", () => {
      renderPage();
      // Should show relative time like "X months ago" or a date - use getAllByText
      const matches = screen.getAllByText(/ago|2024|\\d{1,2}\\/\\d{1,2}/i);
      expect(matches.length).toBeGreaterThan(0);
    });
  });
});
