/**
 * Tests for VOExportPage
 *
 * Tests:
 * - Export list display
 * - Create export modal
 * - Cone search functionality
 * - Export stats panel
 * - Format and status filters
 * - Download and delete operations
 * - Accessibility
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { VOExportPage } from "./VOExportPage";
import type { ExportJob, ConeSearchResult } from "../api/vo-export";

// ============================================================================
// Mocks
// ============================================================================

const mockExportJobs: ExportJob[] = [
  {
    id: "export-1",
    name: "Full Source Catalog",
    format: "votable",
    data_type: "sources",
    filter: {
      data_type: "sources",
      limit: 10000,
    },
    status: "completed",
    record_count: 5000,
    file_size_bytes: 2097152,
    file_size_formatted: "2.00 MB",
    created_at: "2024-01-15T10:00:00Z",
    completed_at: "2024-01-15T10:05:00Z",
    expires_at: "2024-01-22T10:00:00Z",
    download_url: "/api/v1/vo/exports/export-1/download",
    created_by: "admin",
  },
  {
    id: "export-2",
    name: "Region Export",
    format: "fits",
    data_type: "images",
    filter: {
      data_type: "images",
      cone_search: {
        ra: 180.0,
        dec: -30.0,
        radius_arcmin: 10,
      },
    },
    status: "processing",
    record_count: 0,
    file_size_bytes: 0,
    file_size_formatted: "0 B",
    created_at: "2024-01-16T10:00:00Z",
    created_by: "operator",
  },
  {
    id: "export-3",
    name: "Failed Export",
    format: "csv",
    data_type: "catalogs",
    filter: {
      data_type: "catalogs",
    },
    status: "failed",
    record_count: 0,
    file_size_bytes: 0,
    file_size_formatted: "0 B",
    created_at: "2024-01-14T10:00:00Z",
    created_by: "admin",
    error_message: "Timeout exceeded",
  },
];

const mockConeSearchResult: ConeSearchResult = {
  total_matches: 25,
  search_ra: 180.0,
  search_dec: -30.0,
  search_radius: 5,
  sources: [
    {
      id: "src-1",
      name: "Source A",
      ra: 180.01,
      dec: -30.01,
      separation_arcsec: 36,
    },
    {
      id: "src-2",
      name: "Source B",
      ra: 180.02,
      dec: -29.99,
      separation_arcsec: 72,
    },
    {
      id: "src-3",
      name: "Source C",
      ra: 179.98,
      dec: -30.02,
      separation_arcsec: 100,
    },
  ],
};

const mockUseExportJobs = vi.fn();
const mockUseCreateExport = vi.fn();
const mockUseDeleteExport = vi.fn();
const mockUseExportPreview = vi.fn();
const mockUseConeSearch = vi.fn();

vi.mock("../api/vo-export", async () => {
  const actual = await vi.importActual("../api/vo-export");
  return {
    ...actual,
    useExportJobs: () => mockUseExportJobs(),
    useCreateExport: () => mockUseCreateExport(),
    useDeleteExport: () => mockUseDeleteExport(),
    useExportPreview: () => mockUseExportPreview(),
    useConeSearch: () => mockUseConeSearch(),
  };
});

// ============================================================================
// Test Utils
// ============================================================================

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderPage() {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <VOExportPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

// ============================================================================
// Tests
// ============================================================================

describe("VOExportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockUseExportJobs.mockReturnValue({
      data: mockExportJobs,
      isLoading: false,
      error: null,
    });

    mockUseCreateExport.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockExportJobs[0]),
      isPending: false,
      isError: false,
    });

    mockUseDeleteExport.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue("export-1"),
      isPending: false,
    });

    mockUseExportPreview.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({
        estimated_records: 5000,
        estimated_size_bytes: 2097152,
        estimated_time_seconds: 60,
        available_columns: [],
        warnings: [],
      }),
      data: null,
      isPending: false,
    });

    mockUseConeSearch.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockConeSearchResult),
      data: null,
      isPending: false,
    });
  });

  describe("Page Header", () => {
    it("renders page title and description", () => {
      renderPage();

      expect(
        screen.getByRole("heading", { name: /vo export/i })
      ).toBeInTheDocument();
      expect(
        screen.getByText(/export data in virtual observatory formats/i)
      ).toBeInTheDocument();
    });

    it("renders new export button", () => {
      renderPage();

      expect(
        screen.getByRole("button", { name: /new export/i })
      ).toBeInTheDocument();
    });
  });

  describe("Export List", () => {
    it("renders list of exports", () => {
      renderPage();

      expect(screen.getByText("Full Source Catalog")).toBeInTheDocument();
      expect(screen.getByText("Region Export")).toBeInTheDocument();
      expect(screen.getByText("Failed Export")).toBeInTheDocument();
    });

    it("shows export format and data type", () => {
      renderPage();

      expect(screen.getByText(/VOTable • Sources/)).toBeInTheDocument();
      expect(screen.getByText(/FITS • Images/)).toBeInTheDocument();
    });

    it("shows export status badges", () => {
      renderPage();

      expect(screen.getByText("completed")).toBeInTheDocument();
      expect(screen.getByText("processing")).toBeInTheDocument();
      expect(screen.getByText("failed")).toBeInTheDocument();
    });

    it("shows record count and file size", () => {
      renderPage();

      // Record count may appear in stats too
      expect(screen.getAllByText("5,000").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("2.00 MB").length).toBeGreaterThanOrEqual(1);
    });

    it("shows download button for completed exports", () => {
      renderPage();

      const downloadLink = screen.getByRole("link", { name: /download/i });
      expect(downloadLink).toBeInTheDocument();
      expect(downloadLink).toHaveAttribute(
        "href",
        "/api/v1/vo/exports/export-1/download"
      );
    });

    it("shows cancel button for processing exports", () => {
      renderPage();

      expect(
        screen.getByRole("button", { name: /cancel/i })
      ).toBeInTheDocument();
    });

    it("shows delete button for completed/failed exports", () => {
      renderPage();

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      expect(deleteButtons.length).toBeGreaterThanOrEqual(1);
    });

    it("shows error message for failed exports", () => {
      renderPage();

      expect(screen.getByText(/timeout exceeded/i)).toBeInTheDocument();
    });

    it("shows cone search info when present", () => {
      renderPage();

      // Cone search appears in sidebar panel and job card
      expect(screen.getAllByText(/cone search/i).length).toBeGreaterThanOrEqual(
        1
      );
    });

    it("shows empty state when no exports", () => {
      mockUseExportJobs.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderPage();

      expect(screen.getByText("No Exports Yet")).toBeInTheDocument();
    });

    it("shows loading skeleton when loading", () => {
      mockUseExportJobs.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderPage();

      const loadingElements = document.querySelectorAll(".animate-pulse");
      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it("shows error message on failure", () => {
      mockUseExportJobs.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error("Network error"),
      });

      renderPage();

      expect(screen.getByText(/failed to load exports/i)).toBeInTheDocument();
    });
  });

  describe("Filters", () => {
    it("shows format filter dropdown", () => {
      renderPage();

      expect(
        screen.getByRole("combobox", { name: /filter by format/i })
      ).toBeInTheDocument();
    });

    it("shows status filter dropdown", () => {
      renderPage();

      expect(
        screen.getByRole("combobox", { name: /filter by status/i })
      ).toBeInTheDocument();
    });

    it("filters by format", async () => {
      const user = userEvent.setup();
      renderPage();

      const formatSelect = screen.getByRole("combobox", {
        name: /filter by format/i,
      });
      await user.selectOptions(formatSelect, "votable");

      // Only VOTable export should be visible
      expect(screen.getByText("Full Source Catalog")).toBeInTheDocument();
      expect(screen.queryByText("Region Export")).not.toBeInTheDocument();
    });

    it("filters by status", async () => {
      const user = userEvent.setup();
      renderPage();

      const statusSelect = screen.getByRole("combobox", {
        name: /filter by status/i,
      });
      await user.selectOptions(statusSelect, "completed");

      // Only completed export should be visible
      expect(screen.getByText("Full Source Catalog")).toBeInTheDocument();
      expect(screen.queryByText("Region Export")).not.toBeInTheDocument();
    });
  });

  describe("Create Export Modal", () => {
    it("opens create export modal when button clicked", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      expect(
        screen.getByRole("heading", { name: /create vo export/i })
      ).toBeInTheDocument();
    });

    it("allows entering export name", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      const nameInput = screen.getByLabelText(/export name/i);
      await user.type(nameInput, "My Export");

      expect(nameInput).toHaveValue("My Export");
    });

    it("allows selecting format", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      // Format selection - may appear multiple times (modal + sidebar info)
      expect(screen.getAllByText("VOTable").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("FITS").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("CSV").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("JSON").length).toBeGreaterThanOrEqual(1);
    });

    it("allows selecting data type", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      const dataTypeSelect = screen.getByLabelText(/data type/i);
      expect(dataTypeSelect).toBeInTheDocument();

      await user.selectOptions(dataTypeSelect, "images");
      expect(dataTypeSelect).toHaveValue("images");
    });

    it("shows cone search toggle", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      expect(
        screen.getByLabelText(/apply cone search filter/i)
      ).toBeInTheDocument();
    });

    it("shows cone search inputs when enabled", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));
      await user.click(screen.getByLabelText(/apply cone search filter/i));

      // RA/Dec inputs appear both in sidebar and modal - get the modal ones
      const raInputs = screen.getAllByLabelText(/^ra \(deg\)/i);
      const decInputs = screen.getAllByLabelText(/^dec \(deg\)/i);
      expect(raInputs.length).toBeGreaterThanOrEqual(2); // sidebar + modal
      expect(decInputs.length).toBeGreaterThanOrEqual(2);
    });

    it("shows preview button", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      expect(
        screen.getByRole("button", { name: /preview export/i })
      ).toBeInTheDocument();
    });

    it("submits create export request", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue(mockExportJobs[0]);
      mockUseCreateExport.mockReturnValue({
        mutateAsync,
        isPending: false,
        isError: false,
      });

      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      // Find and click the create button in the modal
      const buttons = screen.getAllByRole("button", { name: /create export/i });
      await user.click(buttons[buttons.length - 1]);

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalled();
      });
    });

    it("closes modal on cancel", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      // Find cancel button in modal
      const cancelButtons = screen.getAllByRole("button", { name: /cancel/i });
      await user.click(cancelButtons[cancelButtons.length - 1]);

      await waitFor(() => {
        expect(
          screen.queryByRole("heading", { name: /create vo export/i })
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Cone Search Panel", () => {
    it("renders cone search form", () => {
      renderPage();

      expect(
        screen.getByRole("heading", { name: /cone search/i })
      ).toBeInTheDocument();
      expect(screen.getByLabelText(/^ra \(deg\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^dec \(deg\)/i)).toBeInTheDocument();
    });

    it("allows entering search coordinates", async () => {
      const user = userEvent.setup();
      renderPage();

      const raInput = screen.getByLabelText(/^ra \(deg\)/i);
      const decInput = screen.getByLabelText(/^dec \(deg\)/i);

      await user.type(raInput, "180.0");
      await user.type(decInput, "-30.0");

      expect(raInput).toHaveValue(180);
      expect(decInput).toHaveValue(-30);
    });

    it("performs cone search", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue(mockConeSearchResult);
      mockUseConeSearch.mockReturnValue({
        mutateAsync,
        data: mockConeSearchResult,
        isPending: false,
      });

      renderPage();

      await user.type(screen.getByLabelText(/^ra \(deg\)/i), "180.0");
      await user.type(screen.getByLabelText(/^dec \(deg\)/i), "-30.0");
      await user.click(screen.getByRole("button", { name: /^search$/i }));

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalled();
      });
    });

    it("shows cone search results", async () => {
      mockUseConeSearch.mockReturnValue({
        mutateAsync: vi.fn(),
        data: mockConeSearchResult,
        isPending: false,
      });

      renderPage();

      expect(screen.getByText("Found 25 sources")).toBeInTheDocument();
      expect(screen.getByText(/Source A/)).toBeInTheDocument();
    });
  });

  describe("Export Statistics", () => {
    it("shows total exports count", () => {
      renderPage();

      expect(screen.getByText("Total Exports")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("shows completed count", () => {
      renderPage();

      expect(screen.getByText("Completed")).toBeInTheDocument();
    });

    it("shows in progress count", () => {
      renderPage();

      expect(screen.getByText("In Progress")).toBeInTheDocument();
    });

    it("shows failed count", () => {
      renderPage();

      expect(screen.getByText("Failed")).toBeInTheDocument();
    });
  });

  describe("Supported Formats Info", () => {
    it("shows VOTable format info", () => {
      renderPage();

      expect(screen.getByText("Supported Formats")).toBeInTheDocument();
      expect(screen.getByText("IVOA standard XML format")).toBeInTheDocument();
    });

    it("shows FITS format info", () => {
      renderPage();

      expect(
        screen.getByText("Binary table format with WCS")
      ).toBeInTheDocument();
    });

    it("shows CSV format info", () => {
      renderPage();

      expect(screen.getByText("Comma-separated values")).toBeInTheDocument();
    });

    it("shows JSON format info", () => {
      renderPage();

      expect(
        screen.getByText("JavaScript Object Notation")
      ).toBeInTheDocument();
    });
  });

  describe("Delete Export", () => {
    it("calls delete mutation when delete clicked and confirmed", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue("export-1");
      mockUseDeleteExport.mockReturnValue({
        mutateAsync,
        isPending: false,
      });

      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      renderPage();

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      await user.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mutateAsync).toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it("does not delete when confirmation cancelled", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn();
      mockUseDeleteExport.mockReturnValue({
        mutateAsync,
        isPending: false,
      });

      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

      renderPage();

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      await user.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mutateAsync).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });
  });

  describe("Accessibility", () => {
    it("has accessible page heading", () => {
      renderPage();

      const heading = screen.getByRole("heading", {
        level: 1,
        name: /vo export/i,
      });
      expect(heading).toBeInTheDocument();
    });

    it("has accessible filter labels", () => {
      renderPage();

      expect(
        screen.getByRole("combobox", { name: /filter by format/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("combobox", { name: /filter by status/i })
      ).toBeInTheDocument();
    });

    it("has accessible cone search form", () => {
      renderPage();

      expect(screen.getByLabelText(/^ra \(deg\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^dec \(deg\)/i)).toBeInTheDocument();
    });

    it("has accessible export modal form", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /new export/i }));

      expect(screen.getByLabelText(/export name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/data type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/max records/i)).toBeInTheDocument();
    });
  });
});
