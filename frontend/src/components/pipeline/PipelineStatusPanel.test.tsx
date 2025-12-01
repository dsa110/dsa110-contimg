import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import {
  PipelineStatusPanel,
  type PipelineStatusResponse,
} from "./PipelineStatusPanel";
import apiClient from "../../api/client";

// Mock the API client
vi.mock("../../api/client", () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockApiClient = apiClient as unknown as { get: ReturnType<typeof vi.fn> };

/**
 * Create a test wrapper with QueryClient and Router.
 */
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

/**
 * Sample pipeline status response for testing.
 */
const mockPipelineStatus: PipelineStatusResponse = {
  stages: {
    "convert-uvh5-to-ms": { pending: 2, running: 1, completed: 10, failed: 0 },
    "calibration-solve": { pending: 0, running: 0, completed: 5, failed: 1 },
    "calibration-apply": { pending: 3, running: 0, completed: 4, failed: 0 },
    imaging: { pending: 1, running: 2, completed: 8, failed: 0 },
    validation: { pending: 0, running: 0, completed: 8, failed: 0 },
    crossmatch: { pending: 0, running: 1, completed: 7, failed: 0 },
    photometry: { pending: 0, running: 0, completed: 7, failed: 0 },
    "catalog-setup": { pending: 0, running: 0, completed: 7, failed: 0 },
    "organize-files": { pending: 0, running: 0, completed: 6, failed: 0 },
  },
  total: { pending: 6, running: 4, completed: 62, failed: 1 },
  worker_count: 2,
  last_updated: new Date().toISOString(),
  is_healthy: true,
};

describe("PipelineStatusPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("loading state", () => {
    it("shows loading spinner while fetching", () => {
      // Never resolve the promise to keep loading state
      mockApiClient.get.mockImplementation(() => new Promise(() => {}));

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      // Should show the title
      expect(screen.getByText("Pipeline Status")).toBeInTheDocument();
    });
  });

  describe("successful data fetch", () => {
    beforeEach(() => {
      mockApiClient.get.mockResolvedValue(mockPipelineStatus);
    });

    it("renders all pipeline stages", async () => {
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Convert")).toBeInTheDocument();
      });

      // Check for stage labels
      expect(screen.getByText("CalSolve")).toBeInTheDocument();
      expect(screen.getByText("CalApply")).toBeInTheDocument();
      expect(screen.getByText("Image")).toBeInTheDocument();
      expect(screen.getByText("Valid")).toBeInTheDocument();
      expect(screen.getByText("XMatch")).toBeInTheDocument();
      expect(screen.getByText("Phot")).toBeInTheDocument();
      expect(screen.getByText("Catalog")).toBeInTheDocument();
      expect(screen.getByText("Files")).toBeInTheDocument();
    });

    it("shows summary counts", async () => {
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("6 pending")).toBeInTheDocument();
      });

      expect(screen.getByText("4 running")).toBeInTheDocument();
      expect(screen.getByText("62 completed")).toBeInTheDocument();
      expect(screen.getByText("1 failed")).toBeInTheDocument();
    });

    it("shows worker count", async () => {
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("2 workers")).toBeInTheDocument();
      });
    });

    it("shows healthy status when is_healthy is true", async () => {
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("● Healthy")).toBeInTheDocument();
      });
    });

    it("shows degraded status when is_healthy is false", async () => {
      mockApiClient.get.mockResolvedValue({
        ...mockPipelineStatus,
        is_healthy: false,
      });

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("○ Degraded")).toBeInTheDocument();
      });
    });

    it("renders stage links to jobs list with filter", async () => {
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Convert")).toBeInTheDocument();
      });

      // Find link for imaging stage
      const imagingLink = screen.getByText("Image").closest("a");
      expect(imagingLink).toHaveAttribute("href", "/jobs?stage=imaging");
    });
  });

  describe("compact mode", () => {
    beforeEach(() => {
      mockApiClient.get.mockResolvedValue(mockPipelineStatus);
    });

    it("shows fewer stages in compact mode", async () => {
      render(<PipelineStatusPanel compact />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Convert")).toBeInTheDocument();
      });

      // Should show main stages
      expect(screen.getByText("CalApply")).toBeInTheDocument();
      expect(screen.getByText("Image")).toBeInTheDocument();
      expect(screen.getByText("Valid")).toBeInTheDocument();
      expect(screen.getByText("Files")).toBeInTheDocument();

      // Should NOT show intermediate stages
      expect(screen.queryByText("CalSolve")).not.toBeInTheDocument();
      expect(screen.queryByText("XMatch")).not.toBeInTheDocument();
      expect(screen.queryByText("Phot")).not.toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message when fetch fails", async () => {
      mockApiClient.get.mockRejectedValue(new Error("Network error"));

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(
          screen.getByText("Unable to load pipeline status")
        ).toBeInTheDocument();
      });

      expect(
        screen.getByText("ABSURD workflow manager may not be enabled yet")
      ).toBeInTheDocument();
    });

    it("shows retry button on error", async () => {
      mockApiClient.get.mockRejectedValue(new Error("Network error"));

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /retry/i })
        ).toBeInTheDocument();
      });
    });
  });

  describe("refresh functionality", () => {
    it("calls refetch when refresh button is clicked", async () => {
      mockApiClient.get.mockResolvedValue(mockPipelineStatus);

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Pipeline Status")).toBeInTheDocument();
      });

      // Wait for initial load
      await waitFor(() => {
        expect(mockApiClient.get).toHaveBeenCalledTimes(1);
      });

      // Click refresh button
      const refreshButton = screen.getByTitle("Refresh");
      await userEvent.click(refreshButton);

      // Should trigger another fetch
      await waitFor(() => {
        expect(mockApiClient.get).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("accessibility", () => {
    beforeEach(() => {
      mockApiClient.get.mockResolvedValue(mockPipelineStatus);
    });

    it("stage nodes have descriptive titles", async () => {
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Convert")).toBeInTheDocument();
      });

      // Check that links have title attributes
      const convertLink = screen.getByText("Convert").closest("a");
      expect(convertLink).toHaveAttribute(
        "title",
        "Convert UVH5 files to Measurement Sets"
      );
    });
  });
});
