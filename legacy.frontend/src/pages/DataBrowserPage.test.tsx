/**
 * DataBrowserPage Component Unit Tests
 *
 * Tests verify:
 * 1. Component renders without errors
 * 2. Tab switching functionality
 * 3. Error state display
 * 4. All expected tabs are present
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import DataBrowserPage from "./DataBrowserPage";

// Mock the API queries
vi.mock("../api/queries", () => ({
  usePipelineStatus: vi.fn(() => ({ data: undefined, error: null, isLoading: false })),
}));

// Mock child components to isolate DataBrowserPage testing
vi.mock("../components/DataBrowser/DataList", () => ({
  DataList: () => <div data-testid="data-list">DataList Component</div>,
}));

vi.mock("../components/DataBrowser/FileBrowser", () => ({
  FileBrowser: () => <div data-testid="file-browser">FileBrowser Component</div>,
}));

vi.mock("../components/DataBrowser/BatchJobMonitor", () => ({
  BatchJobMonitor: () => <div data-testid="batch-job-monitor">BatchJobMonitor Component</div>,
}));

vi.mock("../pages/QAPage", () => ({
  default: ({ embedded }: { embedded?: boolean }) => (
    <div data-testid="qa-page">QAPage Component {embedded ? "(embedded)" : ""}</div>
  ),
}));

vi.mock("../pages/CARTAPage", () => ({
  default: ({ embedded }: { embedded?: boolean }) => (
    <div data-testid="carta-page">CARTAPage Component {embedded ? "(embedded)" : ""}</div>
  ),
}));

const { usePipelineStatus } = await import("../api/queries");

describe("DataBrowserPage", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithProviders = () => {
    return render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <DataBrowserPage />
        </QueryClientProvider>
      </BrowserRouter>
    );
  };

  describe("Component Rendering", () => {
    it("should render without errors", () => {
      expect(() => renderWithProviders()).not.toThrow();
    });

    it("should display the page title", () => {
      renderWithProviders();
      expect(screen.getByText("Data Browser")).toBeInTheDocument();
    });

    it("should display all expected tabs", () => {
      renderWithProviders();

      expect(screen.getByRole("tab", { name: /data products/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /file system/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /batch jobs/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /qa tools/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /carta/i })).toBeInTheDocument();
    });

    it("should render DataList component on first tab by default", () => {
      renderWithProviders();
      expect(screen.getByTestId("data-list")).toBeInTheDocument();
    });
  });

  describe("Tab Navigation", () => {
    it("should switch to File System tab when clicked", async () => {
      const user = userEvent.setup();
      renderWithProviders();

      const fileSystemTab = screen.getByRole("tab", { name: /file system/i });
      await user.click(fileSystemTab);

      await waitFor(() => {
        expect(fileSystemTab).toHaveAttribute("aria-selected", "true");
        expect(screen.getByTestId("file-browser")).toBeInTheDocument();
      });
    });

    it("should switch to Batch Jobs tab when clicked", async () => {
      const user = userEvent.setup();
      renderWithProviders();

      const batchJobsTab = screen.getByRole("tab", { name: /batch jobs/i });
      await user.click(batchJobsTab);

      await waitFor(() => {
        expect(batchJobsTab).toHaveAttribute("aria-selected", "true");
        expect(screen.getByTestId("batch-job-monitor")).toBeInTheDocument();
      });
    });

    it("should switch to QA Tools tab when clicked", async () => {
      const user = userEvent.setup();
      renderWithProviders();

      const qaTab = screen.getByRole("tab", { name: /qa tools/i });
      await user.click(qaTab);

      await waitFor(() => {
        expect(qaTab).toHaveAttribute("aria-selected", "true");
        expect(screen.getByTestId("qa-page")).toBeInTheDocument();
      });
    });

    it("should switch to CARTA tab when clicked", async () => {
      const user = userEvent.setup();
      renderWithProviders();

      const cartaTab = screen.getByRole("tab", { name: /carta/i });
      await user.click(cartaTab);

      await waitFor(() => {
        expect(cartaTab).toHaveAttribute("aria-selected", "true");
        expect(screen.getByTestId("carta-page")).toBeInTheDocument();
      });
    });

    it("should return to first tab when Data Products is clicked", async () => {
      const user = userEvent.setup();
      renderWithProviders();

      // Navigate to another tab first
      const cartaTab = screen.getByRole("tab", { name: /carta/i });
      await user.click(cartaTab);

      await waitFor(() => {
        expect(cartaTab).toHaveAttribute("aria-selected", "true");
      });

      // Navigate back to Data Products
      const dataProductsTab = screen.getByRole("tab", { name: /data products/i });
      await user.click(dataProductsTab);

      await waitFor(() => {
        expect(dataProductsTab).toHaveAttribute("aria-selected", "true");
        expect(screen.getByTestId("data-list")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("should display error alert when pipeline status has error", () => {
      vi.mocked(usePipelineStatus).mockReturnValue({
        data: undefined,
        error: new Error("Connection failed"),
        isLoading: false,
      } as any);

      renderWithProviders();

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/error connecting to pipeline api/i)).toBeInTheDocument();
    });

    it("should not display error alert when no error", () => {
      vi.mocked(usePipelineStatus).mockReturnValue({
        data: undefined,
        error: null,
        isLoading: false,
      } as any);

      renderWithProviders();

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  describe("Child Component Props", () => {
    it("should pass embedded=true to QAPage", async () => {
      const user = userEvent.setup();
      renderWithProviders();

      const qaTab = screen.getByRole("tab", { name: /qa tools/i });
      await user.click(qaTab);

      await waitFor(() => {
        expect(screen.getByText(/\(embedded\)/)).toBeInTheDocument();
      });
    });

    it("should pass embedded=true to CARTAPage", async () => {
      const user = userEvent.setup();
      renderWithProviders();

      const cartaTab = screen.getByRole("tab", { name: /carta/i });
      await user.click(cartaTab);

      await waitFor(() => {
        expect(screen.getByText(/\(embedded\)/)).toBeInTheDocument();
      });
    });
  });
});
