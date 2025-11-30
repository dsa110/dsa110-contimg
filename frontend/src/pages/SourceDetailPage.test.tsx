import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import SourceDetailPage from "./SourceDetailPage";

// Mock the hooks
vi.mock("../hooks/useQueries", () => ({
  useSource: vi.fn(),
}));

vi.mock("../stores/appStore", () => ({
  usePreferencesStore: vi.fn(() => vi.fn()),
}));

// Mock error boundary
vi.mock("../components/errors", () => ({
  WidgetErrorBoundary: vi.fn(({ children }) => <>{children}</>),
}));

// Mock components
vi.mock("../components/widgets", () => ({
  AladinLiteViewer: vi.fn(() => <div data-testid="aladin-viewer">Aladin Viewer</div>),
  LightCurveChart: vi.fn(() => <div data-testid="light-curve-chart">Light Curve Chart</div>),
}));

vi.mock("../components/common", () => ({
  Card: vi.fn(({ children, title }) => (
    <div data-testid={`card-${title?.toLowerCase().replace(/\s/g, "-")}`}>
      <h3>{title}</h3>
      {children}
    </div>
  )),
  CoordinateDisplay: vi.fn(() => <div>Coordinates</div>),
  LoadingSpinner: vi.fn(({ label }) => <div>{label}</div>),
  PageSkeleton: vi.fn(() => <div data-testid="page-skeleton">Loading...</div>),
  QAMetrics: vi.fn(({ grade, summary }) => (
    <div data-testid="qa-metrics" data-grade={grade} data-summary={summary}>
      QA Metrics: {grade}
    </div>
  )),
}));

vi.mock("../components/provenance/ProvenanceStrip", () => ({
  default: vi.fn(() => <div>Provenance Strip</div>),
}));

vi.mock("../components/errors/ErrorDisplay", () => ({
  default: vi.fn(() => <div>Error Display</div>),
}));

vi.mock("../components/catalogs", () => ({
  CatalogOverlayPanel: vi.fn(() => <div data-testid="catalog-panel">Catalog Panel</div>),
}));

vi.mock("../components/crossmatch", () => ({
  NearbyObjectsPanel: vi.fn(() => <div data-testid="nearby-panel">Nearby Panel</div>),
  NearbyObject: vi.fn(),
}));

import { useSource } from "../hooks/useQueries";

const mockSourceWithGoodImages = {
  id: "source-123",
  name: "DSA-110 J1234+5678",
  ra_deg: 180.0,
  dec_deg: 45.0,
  contributing_images: [
    { image_id: "img-1", qa_grade: "good", flux_jy: 0.01, created_at: "2025-01-01T00:00:00Z" },
    { image_id: "img-2", qa_grade: "good", flux_jy: 0.012, created_at: "2025-01-02T00:00:00Z" },
    { image_id: "img-3", qa_grade: "warn", flux_jy: 0.011, created_at: "2025-01-03T00:00:00Z" },
  ],
};

const mockSourceWithMixedImages = {
  id: "source-456",
  name: "DSA-110 J9876-5432",
  ra_deg: 90.0,
  dec_deg: -30.0,
  contributing_images: [
    { image_id: "img-1", qa_grade: "fail", flux_jy: 0.01, created_at: "2025-01-01T00:00:00Z" },
    { image_id: "img-2", qa_grade: "fail", flux_jy: 0.012, created_at: "2025-01-02T00:00:00Z" },
    { image_id: "img-3", qa_grade: "good", flux_jy: 0.011, created_at: "2025-01-03T00:00:00Z" },
  ],
};

const mockSourceNoImages = {
  id: "source-789",
  name: "DSA-110 J0000+0000",
  ra_deg: 0.0,
  dec_deg: 0.0,
  contributing_images: [],
};

const renderWithRouter = (sourceId = "source-123") => {
  return render(
    <MemoryRouter initialEntries={[`/sources/${sourceId}`]}>
      <Routes>
        <Route path="/sources/:sourceId" element={<SourceDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("SourceDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    (useSource as any).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Loading source details...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    (useSource as any).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { message: "Failed to load" },
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Error Display")).toBeInTheDocument();
  });

  it("renders not found state when source is null", () => {
    (useSource as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Source not found.")).toBeInTheDocument();
  });

  it("renders source details when loaded", () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithGoodImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getAllByText("DSA-110 J1234+5678").length).toBeGreaterThan(0);
  });

  it("displays QAMetrics when source has contributing images with QA grades", async () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithGoodImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("qa-metrics")).toBeInTheDocument();
    });
  });

  it("computes overall good grade when majority of images are good", async () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithGoodImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    await waitFor(() => {
      const qaMetrics = screen.getByTestId("qa-metrics");
      expect(qaMetrics.getAttribute("data-grade")).toBe("good");
    });
  });

  it("computes overall fail grade when majority of images fail", async () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithMixedImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    await waitFor(() => {
      const qaMetrics = screen.getByTestId("qa-metrics");
      expect(qaMetrics.getAttribute("data-grade")).toBe("fail");
    });
  });

  it("includes summary with image counts", async () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithGoodImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    await waitFor(() => {
      const qaMetrics = screen.getByTestId("qa-metrics");
      const summary = qaMetrics.getAttribute("data-summary");
      expect(summary).toContain("2 good");
      expect(summary).toContain("1 marginal");
      expect(summary).toContain("0 failed");
    });
  });

  it("does not display QAMetrics when no images have QA grades", () => {
    const sourceWithNoQA = {
      ...mockSourceNoImages,
      contributing_images: [
        { image_id: "img-1", flux_jy: 0.01, created_at: "2025-01-01T00:00:00Z" },
      ],
    };

    (useSource as any).mockReturnValue({
      data: sourceWithNoQA,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    // Should not find QA metrics card (Quality Assessment title)
    expect(screen.queryByTestId("card-quality-assessment")).not.toBeInTheDocument();
  });

  it("does not display QAMetrics when no contributing images", () => {
    (useSource as any).mockReturnValue({
      data: mockSourceNoImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    expect(screen.queryByTestId("card-quality-assessment")).not.toBeInTheDocument();
  });

  it("displays light curve when multiple measurements exist", () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithGoodImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByTestId("light-curve-chart")).toBeInTheDocument();
  });

  it("shows contributing images section", () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithGoodImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByTestId("card-contributing-images")).toBeInTheDocument();
  });

  it("displays catalog crossmatch panel", () => {
    (useSource as any).mockReturnValue({
      data: mockSourceWithGoodImages,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByTestId("catalog-panel")).toBeInTheDocument();
  });
});
