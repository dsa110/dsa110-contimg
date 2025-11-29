import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HomePage from "./HomePage";

// Mock the custom hooks
vi.mock("../hooks/useQueries", () => ({
  useImages: vi.fn(),
  useSources: vi.fn(),
  useJobs: vi.fn(),
}));

// Mock child components to simplify tests
vi.mock("../components/summary", () => ({
  StatCardGrid: ({ cards, isLoading }: { cards: unknown[]; isLoading: boolean }) => (
    <div data-testid="stat-card-grid" data-loading={isLoading}>
      {cards.map((card: any, i: number) => (
        <div key={i} data-testid={`stat-card-${card.label}`}>
          {card.label}: {card.value}
        </div>
      ))}
    </div>
  ),
}));

vi.mock("../components/skymap", () => ({
  SkyCoverageMap: ({ pointings }: { pointings: unknown[] }) => (
    <div data-testid="sky-coverage-map" data-pointing-count={pointings.length}>
      Sky Coverage Map
    </div>
  ),
}));

vi.mock("../components/stats", () => ({
  StatsDashboard: ({
    totalCandidates,
    ratedCandidates,
    isLoading,
  }: {
    totalCandidates: number;
    ratedCandidates: number;
    isLoading: boolean;
  }) => (
    <div data-testid="stats-dashboard" data-loading={isLoading}>
      Total: {totalCandidates}, Rated: {ratedCandidates}
    </div>
  ),
  ServiceStatusPanel: () => <div data-testid="service-status-panel">Service Status</div>,
}));

import { useImages, useSources, useJobs } from "../hooks/useQueries";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe("HomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock implementations
    (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
    });
    (useSources as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
    });
    (useJobs as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
    });
  });

  describe("basic rendering", () => {
    it("renders page title", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("DSA-110 Continuum Imaging Pipeline")).toBeInTheDocument();
    });

    it("renders page description", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/Monitor and manage the radio imaging pipeline/)).toBeInTheDocument();
    });

    it("renders Pipeline Overview section", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Pipeline Overview")).toBeInTheDocument();
    });

    it("renders StatCardGrid component", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId("stat-card-grid")).toBeInTheDocument();
    });

    it("renders ServiceStatusPanel", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId("service-status-panel")).toBeInTheDocument();
    });

    it("renders quick links section", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Quick Links")).toBeInTheDocument();
      expect(screen.getByText("Troubleshooting Guide")).toBeInTheDocument();
      expect(screen.getByText("API Health Check")).toBeInTheDocument();
    });
  });

  describe("dashboard cards", () => {
    it("renders Images dashboard card", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Images")).toBeInTheDocument();
      expect(screen.getByText(/Browse processed FITS images/)).toBeInTheDocument();
    });

    it("renders Sources dashboard card", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Sources")).toBeInTheDocument();
      expect(screen.getByText(/Explore detected radio sources/)).toBeInTheDocument();
    });

    it("renders Jobs dashboard card", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Jobs")).toBeInTheDocument();
      expect(screen.getByText(/Monitor pipeline jobs/)).toBeInTheDocument();
    });

    it("dashboard cards link to correct routes", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      const imagesLink = screen.getByText("Images").closest("a");
      const sourcesLink = screen.getByText("Sources").closest("a");
      const jobsLink = screen.getByText("Jobs").closest("a");

      expect(imagesLink).toHaveAttribute("href", "/images");
      expect(sourcesLink).toHaveAttribute("href", "/sources");
      expect(jobsLink).toHaveAttribute("href", "/jobs");
    });
  });

  describe("stat cards", () => {
    it("displays correct counts from hooks", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [{ id: "1" }, { id: "2" }, { id: "3" }],
        isLoading: false,
      });
      (useSources as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [{ id: "s1" }, { id: "s2" }],
        isLoading: false,
      });
      (useJobs as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [{ run_id: "j1" }],
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });

      expect(screen.getByTestId("stat-card-Total Images")).toHaveTextContent("Total Images: 3");
      expect(screen.getByTestId("stat-card-Detected Sources")).toHaveTextContent(
        "Detected Sources: 2"
      );
      expect(screen.getByTestId("stat-card-Pipeline Jobs")).toHaveTextContent("Pipeline Jobs: 1");
    });

    it("shows loading state when data is loading", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: undefined,
        isLoading: true,
      });
      (useSources as ReturnType<typeof vi.fn>).mockReturnValue({
        data: undefined,
        isLoading: true,
      });
      (useJobs as ReturnType<typeof vi.fn>).mockReturnValue({
        data: undefined,
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId("stat-card-grid")).toHaveAttribute("data-loading", "true");
    });

    it("shows 0 for counts when data is undefined", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: undefined,
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId("stat-card-Total Images")).toHaveTextContent("Total Images: 0");
    });
  });

  describe("stats dashboard toggle", () => {
    it("initially hides the stats dashboard", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.queryByTestId("stats-dashboard")).not.toBeInTheDocument();
    });

    it('shows "Show Detailed Stats" button initially', () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Show Detailed Stats")).toBeInTheDocument();
    });

    it("toggles stats dashboard visibility when button clicked", async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      const toggleButton = screen.getByText("Show Detailed Stats");
      fireEvent.click(toggleButton);

      await waitFor(() => {
        expect(screen.getByTestId("stats-dashboard")).toBeInTheDocument();
      });
      expect(screen.getByText("Hide Details")).toBeInTheDocument();
    });

    it("hides stats dashboard when clicking again", async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      // Show dashboard
      fireEvent.click(screen.getByText("Show Detailed Stats"));
      await waitFor(() => {
        expect(screen.getByTestId("stats-dashboard")).toBeInTheDocument();
      });

      // Hide dashboard
      fireEvent.click(screen.getByText("Hide Details"));
      await waitFor(() => {
        expect(screen.queryByTestId("stats-dashboard")).not.toBeInTheDocument();
      });
    });
  });

  describe("rating stats computation", () => {
    it("computes correct rating stats from QA grades", async () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          { id: "1", qa_grade: "good" },
          { id: "2", qa_grade: "good" },
          { id: "3", qa_grade: "warn" },
          { id: "4", qa_grade: "fail" },
          { id: "5", qa_grade: null },
        ],
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });

      // Show dashboard to see stats
      fireEvent.click(screen.getByText("Show Detailed Stats"));

      await waitFor(() => {
        const dashboard = screen.getByTestId("stats-dashboard");
        // 5 total, 4 rated (2 good + 1 warn + 1 fail)
        expect(dashboard).toHaveTextContent("Total: 5, Rated: 4");
      });
    });

    it("handles empty images array", async () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [],
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByText("Show Detailed Stats"));

      await waitFor(() => {
        const dashboard = screen.getByTestId("stats-dashboard");
        expect(dashboard).toHaveTextContent("Total: 0, Rated: 0");
      });
    });
  });

  describe("sky coverage map", () => {
    it("does not render sky map when no pointings available", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [{ id: "1", pointing_ra_deg: null, pointing_dec_deg: null }],
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.queryByTestId("sky-coverage-map")).not.toBeInTheDocument();
    });

    it("renders sky map when images have pointing data", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          { id: "1", pointing_ra_deg: 180.0, pointing_dec_deg: 45.0, qa_grade: "good" },
          { id: "2", pointing_ra_deg: 90.0, pointing_dec_deg: -30.0, qa_grade: "fail" },
        ],
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId("sky-coverage-map")).toBeInTheDocument();
      expect(screen.getByTestId("sky-coverage-map")).toHaveAttribute("data-pointing-count", "2");
    });

    it("filters out images without valid pointing data", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          { id: "1", pointing_ra_deg: 180.0, pointing_dec_deg: 45.0 },
          { id: "2", pointing_ra_deg: null, pointing_dec_deg: 45.0 },
          { id: "3", pointing_ra_deg: 90.0, pointing_dec_deg: null },
        ],
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId("sky-coverage-map")).toHaveAttribute("data-pointing-count", "1");
    });

    it("shows Sky Coverage section title when map is visible", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [{ id: "1", pointing_ra_deg: 180.0, pointing_dec_deg: 45.0 }],
        isLoading: false,
      });

      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Sky Coverage")).toBeInTheDocument();
    });
  });

  describe("quick links", () => {
    it("troubleshooting link has correct href", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      const link = screen.getByText("Troubleshooting Guide");
      expect(link).toHaveAttribute("href", "/docs/troubleshooting.md");
      expect(link).toHaveAttribute("target", "_blank");
    });

    it("API health link has correct href", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      const link = screen.getByText("API Health Check");
      expect(link).toHaveAttribute("href", "/api/health");
      expect(link).toHaveAttribute("target", "_blank");
    });
  });

  describe("infrastructure status section", () => {
    it("renders infrastructure status section", () => {
      render(<HomePage />, { wrapper: createWrapper() });
      expect(screen.getByText("Infrastructure Status")).toBeInTheDocument();
    });
  });
});
