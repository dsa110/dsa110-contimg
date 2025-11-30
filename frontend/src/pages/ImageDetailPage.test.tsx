import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ImageDetailPage from "./ImageDetailPage";

// Mock the hooks
vi.mock("../hooks/useQueries", () => ({
  useImage: vi.fn(),
}));

vi.mock("../stores/appStore", () => ({
  usePreferencesStore: vi.fn(() => vi.fn()),
}));

// Mock error boundary
vi.mock("../components/errors", () => ({
  WidgetErrorBoundary: vi.fn(({ children }) => <>{children}</>),
}));

// Mock components that have complex dependencies
vi.mock("../components/widgets", () => ({
  AladinLiteViewer: vi.fn(() => <div data-testid="aladin-viewer">Aladin Viewer</div>),
  GifPlayer: vi.fn(({ src, onFrameChange }) => (
    <div data-testid="gif-player" data-src={src}>
      GIF Player
      <button onClick={() => onFrameChange?.(0, 10)}>Frame Change</button>
    </div>
  )),
}));

vi.mock("../components/fits", () => ({
  FitsViewer: vi.fn(() => <div data-testid="fits-viewer">FITS Viewer</div>),
}));

vi.mock("../components/common", () => ({
  Card: vi.fn(({ children, title }) => (
    <div data-testid={`card-${title?.toLowerCase().replace(/\s/g, "-")}`}>
      <h3>{title}</h3>
      {children}
    </div>
  )),
  CoordinateDisplay: vi.fn(() => <div>Coordinates</div>),
  ImageThumbnail: vi.fn(() => <div>Thumbnail</div>),
  LoadingSpinner: vi.fn(({ label }) => <div>{label}</div>),
  PageSkeleton: vi.fn(() => <div data-testid="page-skeleton">Loading...</div>),
  Modal: vi.fn(({ children, isOpen }) =>
    isOpen ? <div data-testid="modal">{children}</div> : null
  ),
  QAMetrics: vi.fn(() => <div data-testid="qa-metrics">QA Metrics</div>),
}));

vi.mock("../components/provenance/ProvenanceStrip", () => ({
  default: vi.fn(() => <div>Provenance Strip</div>),
}));

vi.mock("../components/errors/ErrorDisplay", () => ({
  default: vi.fn(() => <div>Error Display</div>),
}));

vi.mock("../components/rating", () => ({
  RatingCard: vi.fn(() => <div data-testid="rating-card">Rating Card</div>),
  RatingTag: vi.fn(),
}));

import { useImage } from "../hooks/useQueries";

const mockImage = {
  id: "test-image-123",
  path: "/data/images/test-image.fits",
  created_at: "2025-01-01T00:00:00Z",
  pointing_ra_deg: 180.0,
  pointing_dec_deg: 45.0,
  qa_grade: "good",
  noise_jy: 0.001,
  dynamic_range: 1000,
};

const renderWithRouter = (imageId = "test-image-123") => {
  return render(
    <MemoryRouter initialEntries={[`/images/${imageId}`]}>
      <Routes>
        <Route path="/images/:imageId" element={<ImageDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("ImageDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    (useImage as any).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByTestId("page-skeleton")).toBeInTheDocument();
  });

  it("renders error state", () => {
    (useImage as any).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { message: "Failed to load" },
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Error Display")).toBeInTheDocument();
  });

  it("renders not found state when image is null", () => {
    (useImage as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Image not found.")).toBeInTheDocument();
  });

  it("renders image details when loaded", () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("test-image.fits")).toBeInTheDocument();
  });

  it("has Animation toggle button", () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Show Animation")).toBeInTheDocument();
  });

  it("toggles GifPlayer visibility when Animation button clicked", async () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    // Initially hidden
    expect(screen.queryByTestId("gif-player")).not.toBeInTheDocument();

    // Click to show
    fireEvent.click(screen.getByText("Show Animation"));

    await waitFor(() => {
      expect(screen.getByTestId("gif-player")).toBeInTheDocument();
    });

    // Button text should change
    expect(screen.getByText("Hide Animation")).toBeInTheDocument();
  });

  it("GifPlayer receives correct src prop", async () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    fireEvent.click(screen.getByText("Show Animation"));

    await waitFor(() => {
      const gifPlayer = screen.getByTestId("gif-player");
      expect(gifPlayer.getAttribute("data-src")).toContain("/images/test-image-123/animation");
    });
  });

  it("toggles FITS Viewer visibility", async () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();

    // Initially hidden
    expect(screen.queryByTestId("fits-viewer")).not.toBeInTheDocument();

    // Click to show
    fireEvent.click(screen.getByText("Show FITS Viewer"));

    await waitFor(() => {
      expect(screen.getByTestId("fits-viewer")).toBeInTheDocument();
    });
  });

  it("displays QA Metrics when qa_grade is present", () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByTestId("qa-metrics")).toBeInTheDocument();
  });

  it("has Download FITS button", () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Download FITS")).toBeInTheDocument();
  });

  it("has Rating toggle button", () => {
    (useImage as any).mockReturnValue({
      data: mockImage,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter();
    expect(screen.getByText("Show Rating")).toBeInTheDocument();
  });
});
