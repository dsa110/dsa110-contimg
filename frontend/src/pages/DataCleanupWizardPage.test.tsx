/**
 * @vitest-environment jsdom
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DataCleanupWizardPage from "./DataCleanupWizardPage";
import * as cleanupApi from "../api/cleanup";

// Mock the cleanup API
vi.mock("../api/cleanup", () => ({
  useCleanupDryRun: vi.fn(),
  useSubmitCleanup: vi.fn(),
  useCleanupHistory: vi.fn(),
}));

// Create query client for tests
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

function renderWithProviders(
  ui: React.ReactElement,
  { route = "/cleanup" } = {}
) {
  const queryClient = createTestQueryClient();
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/cleanup" element={ui} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    ),
    queryClient,
  };
}

describe("DataCleanupWizardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock implementations
    vi.mocked(cleanupApi.useCleanupDryRun).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof cleanupApi.useCleanupDryRun>);

    vi.mocked(cleanupApi.useSubmitCleanup).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof cleanupApi.useSubmitCleanup>);

    vi.mocked(cleanupApi.useCleanupHistory).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof cleanupApi.useCleanupHistory>);
  });

  describe("Wizard Step 1: Filters", () => {
    it("renders filter step by default", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      expect(screen.getByText("Data Cleanup Wizard")).toBeInTheDocument();
      expect(screen.getByText("Select Scope")).toBeInTheDocument();
      expect(screen.getByText("Select Data to Clean Up")).toBeInTheDocument();
    });

    it("shows minimum age slider with default value", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      const slider = screen.getByRole("slider");
      expect(slider).toBeInTheDocument();
      expect(slider).toHaveValue("30");
    });

    it("displays data type options", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      expect(screen.getByText("Measurement Sets")).toBeInTheDocument();
      expect(screen.getByText("Images")).toBeInTheDocument();
      expect(screen.getByText("Logs")).toBeInTheDocument();
      expect(screen.getByText("Temporary Files")).toBeInTheDocument();
      expect(screen.getByText("Cache")).toBeInTheDocument();
    });

    it("allows toggling data types", async () => {
      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      // Temp and Log are selected by default
      const tempButton = screen.getByRole("button", {
        name: /temporary files/i,
      });
      const msButton = screen.getByRole("button", {
        name: /measurement sets/i,
      });

      // Temp should be selected (has blue styling)
      expect(tempButton).toHaveClass("border-blue-500");

      // MS should not be selected
      expect(msButton).not.toHaveClass("border-blue-500");

      // Toggle MS on
      await user.click(msButton);
      expect(msButton).toHaveClass("border-blue-500");

      // Toggle Temp off
      await user.click(tempButton);
      expect(tempButton).not.toHaveClass("border-blue-500");
    });

    it("shows action selection (archive/delete)", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      expect(screen.getByLabelText(/archive/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/delete/i)).toBeInTheDocument();
    });

    it("has archive selected by default", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      const archiveRadio = screen.getByLabelText(/archive/i);
      expect(archiveRadio).toBeChecked();
    });
  });

  describe("Wizard Step 2: Preview", () => {
    it("advances to preview step when Run Preview clicked", async () => {
      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      const previewButton = screen.getByRole("button", {
        name: /run preview/i,
      });
      await user.click(previewButton);

      expect(screen.getByText("Preview Impact")).toBeInTheDocument();
    });

    it("shows loading state during dry-run", async () => {
      vi.mocked(cleanupApi.useCleanupDryRun).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof cleanupApi.useCleanupDryRun>);

      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      await user.click(screen.getByRole("button", { name: /run preview/i }));

      expect(screen.getByText(/analyzing/i)).toBeInTheDocument();
    });

    it("displays dry-run results when loaded", async () => {
      const mockDryRun: cleanupApi.CleanupDryRunResult = {
        affected_count: 150,
        bytes_to_free: 5368709120, // 5 GB
        size_formatted: "5.00 GB",
        by_category: {
          temp: { count: 100, bytes: 2147483648 },
          log: { count: 50, bytes: 3221225472 },
        },
        sample_paths: ["/data/temp/file1.dat"],
        warnings: [],
        can_execute: true,
      };

      vi.mocked(cleanupApi.useCleanupDryRun).mockReturnValue({
        data: mockDryRun,
        isLoading: false,
        error: null,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof cleanupApi.useCleanupDryRun>);

      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      await user.click(screen.getByRole("button", { name: /run preview/i }));

      await waitFor(() => {
        expect(screen.getByText(/150/)).toBeInTheDocument();
        expect(screen.getByText(/5\.00 GB/)).toBeInTheDocument();
      });
    });

    it("shows error state when dry-run fails", async () => {
      vi.mocked(cleanupApi.useCleanupDryRun).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("API error"),
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof cleanupApi.useCleanupDryRun>);

      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      await user.click(screen.getByRole("button", { name: /run preview/i }));

      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  describe("Wizard Step 3: Confirm", () => {
    it("advances to confirm step from preview", async () => {
      const mockDryRun: cleanupApi.CleanupDryRunResult = {
        affected_count: 10,
        bytes_to_free: 1000000,
        size_formatted: "1.00 MB",
        by_category: {},
        sample_paths: [],
        warnings: [],
        can_execute: true,
      };

      vi.mocked(cleanupApi.useCleanupDryRun).mockReturnValue({
        data: mockDryRun,
        isLoading: false,
        error: null,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof cleanupApi.useCleanupDryRun>);

      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      // Go to preview
      await user.click(screen.getByRole("button", { name: /run preview/i }));

      // Go to confirm
      await user.click(screen.getByRole("button", { name: /continue/i }));

      expect(screen.getByText(/confirm/i)).toBeInTheDocument();
    });

    it("requires audit note before submission", async () => {
      const mockDryRun: cleanupApi.CleanupDryRunResult = {
        affected_count: 10,
        bytes_to_free: 1000000,
        size_formatted: "1.00 MB",
        by_category: {},
        sample_paths: [],
        warnings: [],
        can_execute: true,
      };

      vi.mocked(cleanupApi.useCleanupDryRun).mockReturnValue({
        data: mockDryRun,
        isLoading: false,
        error: null,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof cleanupApi.useCleanupDryRun>);

      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      // Navigate to confirm step
      await user.click(screen.getByRole("button", { name: /run preview/i }));
      await user.click(screen.getByRole("button", { name: /continue/i }));

      // Submit button should be disabled without audit note
      const submitButton = screen.getByRole("button", {
        name: /submit cleanup/i,
      });
      expect(submitButton).toBeDisabled();

      // Enter audit note
      const textarea = screen.getByRole("textbox");
      await user.type(textarea, "Quarterly cleanup of temp files");

      // Submit button should now be enabled
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe("Wizard Step 4: Complete", () => {
    it("shows success message after submission", async () => {
      const mockDryRun: cleanupApi.CleanupDryRunResult = {
        affected_count: 10,
        bytes_to_free: 1000000,
        size_formatted: "1.00 MB",
        by_category: {},
        sample_paths: [],
        warnings: [],
        can_execute: true,
      };

      vi.mocked(cleanupApi.useCleanupDryRun).mockReturnValue({
        data: mockDryRun,
        isLoading: false,
        error: null,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof cleanupApi.useCleanupDryRun>);

      const mockMutateAsync = vi.fn().mockResolvedValue({
        id: "cleanup-123",
        run_id: "run-456",
        status: "running",
        submitted_at: new Date().toISOString(),
        action: "archive",
        filters: {},
        submitted_by: "test-user",
        audit_note: "Quarterly cleanup",
      } as cleanupApi.CleanupJob);

      vi.mocked(cleanupApi.useSubmitCleanup).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof cleanupApi.useSubmitCleanup>);

      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      // Navigate through steps
      await user.click(screen.getByRole("button", { name: /run preview/i }));
      await user.click(screen.getByRole("button", { name: /continue/i }));

      // Enter audit note
      await user.type(
        screen.getByRole("textbox"),
        "Quarterly cleanup of temp files"
      );

      // Submit
      await user.click(screen.getByRole("button", { name: /submit cleanup/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled();
        expect(screen.getByText(/cleanup-123/)).toBeInTheDocument();
      });
    });
  });

  describe("Navigation", () => {
    it("allows going back from preview to filters", async () => {
      renderWithProviders(<DataCleanupWizardPage />);
      const user = userEvent.setup();

      // Go to preview
      await user.click(screen.getByRole("button", { name: /run preview/i }));
      expect(screen.getByText("Preview Impact")).toBeInTheDocument();

      // Go back
      await user.click(screen.getByRole("button", { name: /back/i }));
      expect(screen.getByText("Select Filters")).toBeInTheDocument();
    });

    it("shows step indicator progress", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      // Check for step indicators
      const stepIndicators = screen.getAllByRole("listitem");
      expect(stepIndicators.length).toBeGreaterThanOrEqual(4);
    });
  });

  describe("Cleanup History", () => {
    it("displays past cleanup jobs", () => {
      const mockHistory: cleanupApi.CleanupJob[] = [
        {
          id: "job-1",
          run_id: "run-1",
          status: "completed",
          submitted_at: "2024-01-15T10:00:00Z",
          completed_at: "2024-01-15T10:30:00Z",
          items_processed: 100,
          bytes_freed: 1073741824,
          action: "archive",
          filters: {},
          submitted_by: "admin",
          audit_note: "Monthly cleanup",
        },
        {
          id: "job-2",
          run_id: "run-2",
          status: "running",
          submitted_at: "2024-01-20T14:00:00Z",
          items_processed: 50,
          bytes_freed: 0,
          action: "delete",
          filters: {},
          submitted_by: "admin",
          audit_note: "Urgent cleanup",
        },
      ];

      vi.mocked(cleanupApi.useCleanupHistory).mockReturnValue({
        data: mockHistory,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof cleanupApi.useCleanupHistory>);

      renderWithProviders(<DataCleanupWizardPage />);

      expect(screen.getByText(/recent cleanup jobs/i)).toBeInTheDocument();
      expect(screen.getByText("job-1")).toBeInTheDocument();
      expect(screen.getByText("job-2")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has accessible form controls", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      // Check for accessible labels
      expect(screen.getByLabelText(/minimum age/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/archive/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/delete/i)).toBeInTheDocument();
    });

    it("has proper heading hierarchy", () => {
      renderWithProviders(<DataCleanupWizardPage />);

      const h1 = screen.getByRole("heading", { level: 1 });
      expect(h1).toHaveTextContent("Data Cleanup Wizard");

      const h2Elements = screen.getAllByRole("heading", { level: 2 });
      expect(h2Elements.length).toBeGreaterThan(0);
    });
  });
});
