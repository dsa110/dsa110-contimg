import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ReactNode } from "react";
import { useImageDetail } from "./useImageDetail";
import apiClient from "../api/client";

// Mock the API client
vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    delete: vi.fn(),
  },
  noRetry: vi.fn(() => ({})),
}));

// Mock the preferences store
const mockAddRecentImage = vi.fn();
vi.mock("../stores/appStore", () => ({
  usePreferencesStore: (selector: (state: { addRecentImage: typeof mockAddRecentImage }) => unknown) =>
    selector({ addRecentImage: mockAddRecentImage }),
}));

// Mock useImage hook
vi.mock("./useQueries", () => ({
  useImage: vi.fn(() => ({
    data: {
      id: "test-image-1",
      path: "/path/to/image.fits",
      qa_grade: "good",
      pointing_ra_deg: 180.5,
      pointing_dec_deg: 45.0,
      created_at: "2024-01-15T10:00:00Z",
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

describe("useImageDetail", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  describe("initial state", () => {
    it("returns image data and loading state", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      expect(result.current.image).toBeDefined();
      expect(result.current.image?.id).toBe("test-image-1");
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("provides encoded image ID", () => {
      const { result } = renderHook(() => useImageDetail("test image/with spaces"), { wrapper });

      expect(result.current.encodedImageId).toBe("test%20image%2Fwith%20spaces");
    });

    it("extracts filename from path", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      expect(result.current.filename).toBe("image.fits");
    });
  });

  describe("viewer state", () => {
    it("initializes with sky viewer open", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      expect(result.current.showSkyViewer).toBe(true);
      expect(result.current.showFitsViewer).toBe(false);
      expect(result.current.showGifPlayer).toBe(false);
      expect(result.current.showRatingCard).toBe(false);
    });

    it("toggles FITS viewer", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      act(() => {
        result.current.toggleFitsViewer();
      });

      expect(result.current.showFitsViewer).toBe(true);

      act(() => {
        result.current.toggleFitsViewer();
      });

      expect(result.current.showFitsViewer).toBe(false);
    });

    it("toggles GIF player", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      act(() => {
        result.current.toggleGifPlayer();
      });

      expect(result.current.showGifPlayer).toBe(true);
    });

    it("toggles rating card", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      act(() => {
        result.current.toggleRatingCard();
      });

      expect(result.current.showRatingCard).toBe(true);
    });

    it("toggles sky viewer", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      act(() => {
        result.current.toggleSkyViewer();
      });

      expect(result.current.showSkyViewer).toBe(false);
    });
  });

  describe("delete modal", () => {
    it("initially has delete modal closed", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      expect(result.current.showDeleteModal).toBe(false);
      expect(result.current.deleteError).toBeNull();
      expect(result.current.isDeleting).toBe(false);
    });

    it("opens and closes delete modal", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      act(() => {
        result.current.openDeleteModal();
      });

      expect(result.current.showDeleteModal).toBe(true);

      act(() => {
        result.current.closeDeleteModal();
      });

      expect(result.current.showDeleteModal).toBe(false);
    });

    it("clears delete error when closing modal", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      // Simulate an error scenario
      act(() => {
        result.current.openDeleteModal();
      });

      act(() => {
        result.current.closeDeleteModal();
      });

      expect(result.current.deleteError).toBeNull();
    });
  });

  describe("provenance", () => {
    it("provides mapped provenance data", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      expect(result.current.provenance).toBeDefined();
    });
  });

  describe("FITS URL", () => {
    it("provides FITS download URL", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      expect(result.current.fitsUrl).toContain("/images/");
      expect(result.current.fitsUrl).toContain("/fits");
    });
  });

  describe("animation URL", () => {
    it("provides animation URL", () => {
      const { result } = renderHook(() => useImageDetail("test-image-1"), { wrapper });

      expect(result.current.animationUrl).toContain("/images/");
      expect(result.current.animationUrl).toContain("/animation");
    });
  });
});
