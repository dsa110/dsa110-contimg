import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HomePage from "./HomePage";
import { ROUTES } from "../constants/routes";
import type { ImageSummary, JobSummary } from "../types";

const { mockUsePipelineStatus } = vi.hoisted(() => ({
  mockUsePipelineStatus: vi.fn(),
}));

vi.mock("../hooks/useQueries", () => ({
  useImages: vi.fn(),
  useSources: vi.fn(),
  useJobs: vi.fn(),
}));

vi.mock("../components/pipeline", () => ({
  PipelineStatusPanel: () => (
    <div data-testid="pipeline-status-panel">Pipeline Status Panel</div>
  ),
  usePipelineStatus: mockUsePipelineStatus,
}));

vi.mock("../components/skymap", () => ({
  SkyCoverageMap: ({ pointings }: { pointings: Array<{ id: string }> }) => (
    <div data-testid="sky-coverage-map" data-pointing-count={pointings.length}>
      Sky Coverage Map
    </div>
  ),
  SkyCoverageMapVAST: ({ pointings }: { pointings: Array<{ id: string }> }) => (
    <div
      data-testid="sky-coverage-map-vast"
      data-pointing-count={pointings.length}
    >
      Sky Coverage Map VAST
    </div>
  ),
}));

vi.mock("../components/stats", () => ({
  ServiceStatusPanel: () => (
    <div data-testid="service-status-panel">Service Status</div>
  ),
}));

import { useImages, useSources, useJobs } from "../hooks/useQueries";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  Wrapper.displayName = "TestWrapper";
  return Wrapper;
};

const renderPage = () => render(<HomePage />, { wrapper: createWrapper() });

const asImage = (partial: Partial<ImageSummary>): ImageSummary =>
  ({
    id: partial.id ?? "img-1",
    path: partial.path ?? "/data/image.fits",
    qa_grade: partial.qa_grade ?? "good",
    created_at: partial.created_at ?? new Date().toISOString(),
    ...partial,
  } as ImageSummary);

const asJob = (partial: Partial<JobSummary> & { run_id: string }): JobSummary =>
  ({
    run_id: partial.run_id,
    status: partial.status ?? "running",
    started_at: partial.started_at ?? new Date().toISOString(),
    finished_at: partial.finished_at,
  } as JobSummary);

describe("HomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    mockUsePipelineStatus.mockReturnValue({
      isPlaceholderData: true,
      data: undefined,
    });
  });

  describe("hero section", () => {
    it("renders the primary heading and description", () => {
      renderPage();

      expect(screen.getByText("Operational Dashboard")).toBeInTheDocument();
      expect(
        screen.getByText(
          /Monitor sky coverage and pipeline activity across the imaging stack/i
        )
      ).toBeInTheDocument();
    });

    it("links hero actions to the correct routes", () => {
      renderPage();

      expect(
        screen.getByRole("link", { name: /browse images/i })
      ).toHaveAttribute("href", ROUTES.IMAGES.LIST);
      expect(screen.getByRole("link", { name: /view jobs/i })).toHaveAttribute(
        "href",
        ROUTES.JOBS.LIST
      );
    });

    it("displays computed hero metrics from hook data", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          asImage({ id: "img-1" }),
          asImage({ id: "img-2" }),
          asImage({ id: "img-3" }),
        ],
        isLoading: false,
      });
      (useSources as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [{ id: "src-1" }, { id: "src-2" }],
        isLoading: false,
      });
      (useJobs as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          asJob({ run_id: "job-1", status: "running" }),
          asJob({ run_id: "job-2", status: "pending" }),
          asJob({
            run_id: "job-3",
            status: "completed",
            finished_at: "2024-01-01T03:00:00Z",
          }),
          asJob({
            run_id: "job-4",
            status: "completed",
            finished_at: "2024-01-01T04:00:00Z",
          }),
        ],
        isLoading: false,
      });

      renderPage();

      const imagesCard = screen.getByText("Images").closest("div")!;
      expect(within(imagesCard).getByText("3")).toBeInTheDocument();

      const sourcesCard = screen.getByText("Sources").closest("div")!;
      expect(within(sourcesCard).getByText("2")).toBeInTheDocument();

      const activeJobsCard = screen.getByText("Active jobs").closest("div")!;
      expect(within(activeJobsCard).getByText("2")).toBeInTheDocument();

      const completedJobsCard = screen
        .getByText("Completed jobs")
        .closest("div")!;
      expect(within(completedJobsCard).getByText("2")).toBeInTheDocument();
    });
  });

  describe("pipeline status", () => {
    it("shows loading badge while placeholder data is used", () => {
      renderPage();
      expect(screen.getByText("Loading...")).toBeInTheDocument();
      expect(screen.getByTestId("pipeline-status-panel")).toBeInTheDocument();
    });

    it("displays health label based on hook result", () => {
      mockUsePipelineStatus.mockReturnValue({
        isPlaceholderData: false,
        data: {
          is_healthy: false,
          last_updated: "2024-01-01T00:00:00Z",
        },
      });

      renderPage();

      expect(screen.getByText("Attention needed")).toBeInTheDocument();
    });
  });

  describe("sky coverage map", () => {
    it("renders map when images include pointing metadata", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          asImage({
            id: "img-1",
            pointing_ra_deg: 123.4,
            pointing_dec_deg: -32.1,
          }),
          asImage({
            id: "img-2",
            pointing_ra_deg: 45.6,
            pointing_dec_deg: 0.1,
          }),
        ],
        isLoading: false,
      });

      renderPage();

      const skyMap = screen.getByTestId("sky-coverage-map-vast");
      expect(skyMap).toHaveAttribute("data-pointing-count", "2");
    });

    it("shows placeholder text when no pointings are available", () => {
      (useImages as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          asImage({
            id: "img-1",
            pointing_ra_deg: null,
            pointing_dec_deg: null,
          }),
        ],
        isLoading: false,
      });

      renderPage();

      expect(screen.queryByTestId("sky-coverage-map")).not.toBeInTheDocument();
      expect(
        screen.getByText(/Pointings will appear here once image metadata/i)
      ).toBeInTheDocument();
    });
  });

  describe("recent jobs", () => {
    it("shows loading state while jobs query is fetching", () => {
      (useJobs as ReturnType<typeof vi.fn>).mockReturnValue({
        data: undefined,
        isLoading: true,
      });

      renderPage();

      expect(screen.getByText("Loading jobs...")).toBeInTheDocument();
    });

    it("shows fallback text when no jobs exist", () => {
      renderPage();
      expect(
        screen.getByText("Awaiting new pipeline submissions.")
      ).toBeInTheDocument();
    });

    it("renders job entries when data is available", () => {
      (useJobs as ReturnType<typeof vi.fn>).mockReturnValue({
        data: [
          asJob({
            run_id: "job-100",
            status: "completed",
            finished_at: "2024-01-01T02:00:00Z",
          }),
          asJob({ run_id: "job-200", status: "running" }),
        ],
        isLoading: false,
      });

      renderPage();

      expect(screen.getByText("job-100")).toBeInTheDocument();
      expect(screen.getByText("job-200")).toBeInTheDocument();
      expect(screen.getByText("Completed")).toBeInTheDocument();
      expect(screen.getByText("Running")).toBeInTheDocument();
    });
  });

  describe("quick links", () => {
    it("renders troubleshooting link with correct attributes", () => {
      renderPage();
      const link = screen.getByRole("link", {
        name: /troubleshooting guide/i,
      });
      expect(link).toHaveAttribute("href", "/docs/troubleshooting.md");
      expect(link).toHaveAttribute("target", "_blank");
    });

    it("renders API health link with correct attributes", () => {
      renderPage();
      const link = screen.getByRole("link", { name: /api health check/i });
      expect(link).toHaveAttribute("href", "/api/health");
      expect(link).toHaveAttribute("target", "_blank");
    });
  });

  it("renders infrastructure status panel", () => {
    renderPage();
    expect(screen.getByTestId("service-status-panel")).toBeInTheDocument();
  });
});
