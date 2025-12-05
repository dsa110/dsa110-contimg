import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MSDetailPage from "./MSDetailPage";

// Mock the hooks
vi.mock("../hooks/useQueries", () => ({
  useMS: vi.fn(),
}));

// Mock config with mutable features for testing
// Note: Using object that gets imported/exported so we can modify it in tests
vi.mock("../config", async () => {
  const actual = await vi.importActual<typeof import("../config")>("../config");
  return {
    ...actual,
    FEATURES: {
      ...actual.FEATURES,
      enableCARTA: true,
      enableCalibrationComparison: true,
    },
  };
});

// Import FEATURES so we can modify it in tests
import { FEATURES } from "../config";

import { useMS } from "../hooks/useQueries";

const mockUseMS = vi.mocked(useMS);

describe("MSDetailPage", () => {
  let queryClient: QueryClient;

  const mockMS = {
    path: "/data/dsa110/ms/2024-01-15/test-ms.ms",
    pointing_ra_deg: 180.5,
    pointing_dec_deg: 45.25,
    created_at: "2024-01-15T10:00:00Z",
    qa_grade: "good",
    qa_summary: "All calibrations passed",
    run_id: "run-123",
    calibrator_matches: [
      { type: "bandpass", cal_table: "/data/cal/bandpass-2024.cal" },
      { type: "gain", cal_table: "/data/cal/gain-2024.cal" },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const renderPage = (msPath = "2024-01-15/test-ms.ms") => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/ms/${msPath}`]}>
          <Routes>
            <Route path="/ms/*" element={<MSDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe("loading state", () => {
    it("shows loading message when loading", () => {
      mockUseMS.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      expect(
        screen.getByText(/loading measurement set details/i)
      ).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error display when fetch fails", () => {
      mockUseMS.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Not found"),
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      expect(
        screen.getByRole("button", { name: /retry/i })
      ).toBeInTheDocument();
    });

    it("calls refetch when retry clicked", async () => {
      const refetch = vi.fn();
      mockUseMS.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Not found"),
        refetch,
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      await userEvent.click(screen.getByRole("button", { name: /retry/i }));
      expect(refetch).toHaveBeenCalled();
    });
  });

  describe("not found state", () => {
    it("shows not found message when no data", () => {
      mockUseMS.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      expect(
        screen.getByText(/measurement set not found/i)
      ).toBeInTheDocument();
    });

    it("shows back to images link when not found", () => {
      mockUseMS.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      expect(
        screen.getByRole("link", { name: /back to images/i })
      ).toBeInTheDocument();
    });
  });

  describe("with data", () => {
    beforeEach(() => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);
    });

    it("renders filename in heading", () => {
      renderPage();
      // Filename might appear multiple places
      const matches = screen.getAllByText(/test-ms\.ms/i);
      expect(matches.length).toBeGreaterThan(0);
    });

    it("renders back to images link", () => {
      renderPage();
      const links = screen.getAllByRole("link", { name: /back to images/i });
      expect(links[0]).toHaveAttribute("href", "/images");
    });

    it("renders ProvenanceStrip", () => {
      renderPage();
      // ProvenanceStrip should be rendered with MS provenance data
      // Check for provenance strip class
      expect(document.querySelector(".provenance-strip")).toBeInTheDocument();
    });
  });

  describe("coordinates display", () => {
    beforeEach(() => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);
    });

    it("renders Pointing card with coordinates", () => {
      renderPage();
      expect(screen.getByText("Pointing")).toBeInTheDocument();
    });

    it("displays CoordinateDisplay component", () => {
      renderPage();
      // CoordinateDisplay should show the RA/Dec values
      expect(screen.getByText(/180/)).toBeInTheDocument();
    });
  });

  describe("calibration display", () => {
    it("shows calibration tables when present", () => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      // Look for calibration-related text
      const calibMatches = screen.getAllByText(/calibration|bandpass|gain/i);
      expect(calibMatches.length).toBeGreaterThan(0);
    });

    it("shows calibration count subtitle", () => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      expect(screen.getByText(/2 calibration tables/i)).toBeInTheDocument();
    });

    it("shows no calibration message when none applied", () => {
      mockUseMS.mockReturnValue({
        data: { ...mockMS, calibrator_matches: [] },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      expect(
        screen.getByText(/no calibration tables applied/i)
      ).toBeInTheDocument();
    });
  });

  describe("QA grade display", () => {
    it("shows quality card when qa_grade present", () => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      expect(screen.getByText("Quality")).toBeInTheDocument();
    });

    it("shows QAMetrics component", () => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);

      renderPage();
      // QAMetrics should render the grade - might appear multiple places
      const matches = screen.getAllByText(/good/i);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  describe("action buttons", () => {
    beforeEach(() => {
      // Reset feature flags to defaults
      (FEATURES as { enableCARTA: boolean }).enableCARTA = true;
      (
        FEATURES as { enableCalibrationComparison: boolean }
      ).enableCalibrationComparison = true;

      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);
    });

    it("renders Download MS button", () => {
      renderPage();
      expect(
        screen.getByRole("button", { name: /download ms/i })
      ).toBeInTheDocument();
    });

    it("renders Open in CARTA button when feature enabled", () => {
      (FEATURES as { enableCARTA: boolean }).enableCARTA = true;
      renderPage();
      expect(
        screen.getByRole("button", { name: /open in carta/i })
      ).toBeInTheDocument();
    });

    it("hides Open in CARTA button when feature disabled", () => {
      (FEATURES as { enableCARTA: boolean }).enableCARTA = false;
      renderPage();
      expect(
        screen.queryByRole("button", { name: /open in carta/i })
      ).not.toBeInTheDocument();
    });

    it("renders View QA Report link when qa_grade present", () => {
      renderPage();
      expect(
        screen.getByRole("link", { name: /view qa report/i })
      ).toBeInTheDocument();
    });
  });

  describe("quick info section", () => {
    beforeEach(() => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);
    });

    it("shows created date", () => {
      renderPage();
      // Look for created-related text - might appear multiple places
      const matches = screen.getAllByText(/created|date|2024/i);
      expect(matches.length).toBeGreaterThan(0);
    });

    it("shows pipeline run link", () => {
      renderPage();
      expect(screen.getByText(/pipeline run/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /run-123/i })).toHaveAttribute(
        "href",
        "/jobs/run-123"
      );
    });
  });

  describe("metadata section", () => {
    beforeEach(() => {
      mockUseMS.mockReturnValue({
        data: mockMS,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMS>);
    });

    it("shows full path in metadata", () => {
      renderPage();
      expect(screen.getByText("Metadata")).toBeInTheDocument();
      expect(screen.getByText(mockMS.path)).toBeInTheDocument();
    });
  });
});
