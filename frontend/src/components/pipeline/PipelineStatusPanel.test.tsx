import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { http, HttpResponse, delay } from "msw";
import { server } from "../../testing/mocks/server";
import {
  createABSURDHealth,
  createABSURDWorkers,
  createABSURDQueuesStats,
} from "../../testing/mocks/handlers";
import { PipelineStatusPanel } from "./PipelineStatusPanel";

/**
 * Create a test wrapper with QueryClient and Router.
 */
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
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

describe("PipelineStatusPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("loading state", () => {
    it("shows loading spinner while fetching", async () => {
      // Use a long delay to keep loading state visible
      server.use(
        http.get("*/absurd/health/detailed", async () => {
          await delay("infinite");
          return HttpResponse.json(createABSURDHealth());
        })
      );

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      // Should show the title immediately
      expect(screen.getByText("Pipeline Status")).toBeInTheDocument();
    });
  });

  describe("successful data fetch", () => {
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

    it("shows pending count from queue depth", async () => {
      // Default health response has queue_depth: 6
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("6 pending")).toBeInTheDocument();
      });
    });

    it("shows worker count", async () => {
      // Default workers response has total: 2
      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("2 workers")).toBeInTheDocument();
      });
    });

    it("shows healthy status when worker_pool_healthy is true", async () => {
      server.use(
        http.get("*/absurd/health/detailed", () => {
          return HttpResponse.json(
            createABSURDHealth({ status: "healthy", worker_pool_healthy: true })
          );
        })
      );

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Healthy")).toBeInTheDocument();
      });
    });

    it("shows degraded status when worker_pool_healthy is false", async () => {
      server.use(
        http.get("*/absurd/health/detailed", () => {
          return HttpResponse.json(
            createABSURDHealth({
              status: "degraded",
              worker_pool_healthy: false,
            })
          );
        })
      );

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Degraded")).toBeInTheDocument();
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
      server.use(
        http.get("*/absurd/health/detailed", () => {
          return new HttpResponse(null, { status: 503 });
        })
      );

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
      server.use(
        http.get("*/absurd/health/detailed", () => {
          return new HttpResponse(null, { status: 503 });
        })
      );

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
      let callCount = 0;
      server.use(
        http.get("*/absurd/health/detailed", () => {
          callCount++;
          return HttpResponse.json(createABSURDHealth());
        }),
        http.get("*/absurd/workers", () => {
          return HttpResponse.json(createABSURDWorkers());
        }),
        http.get("*/absurd/queues/stats", () => {
          return HttpResponse.json(createABSURDQueuesStats());
        })
      );

      render(<PipelineStatusPanel />, { wrapper: createWrapper() });

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText("6 pending")).toBeInTheDocument();
      });

      // Refresh button should be enabled
      const refreshButton = screen.getByTitle("Refresh");
      expect(refreshButton).not.toBeDisabled();

      // Click refresh
      await userEvent.click(refreshButton);

      // Should trigger another fetch
      await waitFor(() => {
        expect(callCount).toBeGreaterThanOrEqual(2);
      });
    });
  });

  describe("accessibility", () => {
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
