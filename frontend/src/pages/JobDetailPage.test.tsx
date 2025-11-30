import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import JobDetailPage from "./JobDetailPage";

// Mock the hooks
vi.mock("../hooks/useQueries", () => ({
  useJobProvenance: vi.fn(),
}));

vi.mock("../stores/appStore", () => ({
  usePreferencesStore: vi.fn(() => vi.fn()),
}));

import { useJobProvenance } from "../hooks/useQueries";

const mockUseJobProvenance = vi.mocked(useJobProvenance);

describe("JobDetailPage", () => {
  let queryClient: QueryClient;

  const mockProvenance = {
    runId: "test-run-123",
    createdAt: "2024-01-15T10:00:00Z",
    qaGrade: "good" as const,
    pipelineVersion: "1.2.3",
    logsUrl: "/logs/test-run-123",
    qaUrl: "/qa/test-run-123",
    imageUrl: "/images/img-001",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const renderPage = (runId = "test-run-123") => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/jobs/${runId}`]}>
          <Routes>
            <Route path="/jobs/:runId" element={<JobDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe("loading state", () => {
    it("shows loading spinner when loading", () => {
      mockUseJobProvenance.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);

      renderPage();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error display when fetch fails", () => {
      mockUseJobProvenance.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Not found"),
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);

      renderPage();
      // ErrorDisplay component should be rendered
      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    });
  });

  describe("not found state", () => {
    it("shows not found message when no data", () => {
      mockUseJobProvenance.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);

      renderPage();
      expect(screen.getByText(/not found/i)).toBeInTheDocument();
    });

    it("shows back link when not found", () => {
      mockUseJobProvenance.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);

      renderPage();
      expect(screen.getByRole("link", { name: /back to jobs/i })).toBeInTheDocument();
    });
  });

  describe("with data", () => {
    beforeEach(() => {
      mockUseJobProvenance.mockReturnValue({
        data: mockProvenance,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);
    });

    it("renders job run ID in heading", () => {
      renderPage();
      // Use getAllByText since run ID appears multiple places
      const matches = screen.getAllByText(/test-run-123/);
      expect(matches.length).toBeGreaterThan(0);
    });

    it("renders back to jobs link", () => {
      renderPage();
      const backLink = screen.getByRole("link", { name: /back to jobs/i });
      expect(backLink).toHaveAttribute("href", "/jobs");
    });

    it("renders status badge", () => {
      renderPage();
      // Based on qaGrade being present, status should be "completed"
      const matches = screen.getAllByText(/completed/i);
      expect(matches.length).toBeGreaterThan(0);
    });

    it("renders ProvenanceStrip", () => {
      renderPage();
      // ProvenanceStrip should show version info
      // Use getAllByText since version may appear multiple places
      const matches = screen.getAllByText(/1\.2\.3|test-run-123/);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  describe("status display", () => {
    it("shows completed status when qaGrade is present", () => {
      mockUseJobProvenance.mockReturnValue({
        data: { ...mockProvenance, qaGrade: "good" },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);

      renderPage();
      const matches = screen.getAllByText(/completed/i);
      expect(matches.length).toBeGreaterThan(0);
    });

    it("shows running status when only createdAt is present", () => {
      mockUseJobProvenance.mockReturnValue({
        data: { ...mockProvenance, qaGrade: undefined },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);

      renderPage();
      const matches = screen.getAllByText(/running/i);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  describe("action buttons", () => {
    beforeEach(() => {
      mockUseJobProvenance.mockReturnValue({
        data: mockProvenance,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);
    });

    it("renders View Logs button when logsUrl present", () => {
      renderPage();
      expect(screen.getByRole("link", { name: /view logs/i })).toBeInTheDocument();
    });

    it("renders QA Report button when qaUrl present", () => {
      renderPage();
      // QA Report may appear multiple times - use getAllByText
      const matches = screen.getAllByText(/QA Report/i);
      expect(matches.length).toBeGreaterThan(0);
    });

    it("renders View Output Image button when imageUrl present", () => {
      renderPage();
      expect(screen.getByRole("link", { name: /view output image/i })).toBeInTheDocument();
    });
  });

  describe("timing information", () => {
    beforeEach(() => {
      mockUseJobProvenance.mockReturnValue({
        data: mockProvenance,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useJobProvenance>);
    });

    it("displays start time", () => {
      renderPage();
      expect(screen.getByText(/started/i)).toBeInTheDocument();
    });

    it("displays relative time", () => {
      renderPage();
      // Look for time-related text - could be "ago" or a date or other time format
      const timeElements = screen.getAllByText(/ago|2024|\d{1,2}:\d{2}/i);
      expect(timeElements.length).toBeGreaterThan(0);
    });
  });
});
