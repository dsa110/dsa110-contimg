/**
 * Tests for useImageDetail hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useImageDetail } from "./useImageDetail";
import apiClient from "../api/client";

// Mock the API client
vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    delete: vi.fn(),
    post: vi.fn(),
  },
  noRetry: vi.fn(() => ({})),
}));

// Mock the preferences store
const mockAddRecentImage = vi.fn();
vi.mock("../stores/appStore", () => ({
  usePreferencesStore: (
    selector: (state: { addRecentImage: typeof mockAddRecentImage }) => unknown
  ) => selector({ addRecentImage: mockAddRecentImage }),
}));

// Mock useImage from useQueries
const mockRefetch = vi.fn();
vi.mock("./useQueries", () => ({
  useImage: vi.fn((imageId: string | undefined) => {
    if (!imageId) {
      return {
        data: undefined,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      };
    }
    return {
      data: {
        id: imageId,
        path: "/data/images/test-image.fits",
        created_at: "2024-01-01T00:00:00Z",
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    };
  }),
}));

// Create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useImageDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.location
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("basic functionality", () => {
    it("returns image data when imageId is provided", () => {
      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      expect(result.current.image).toBeDefined();
      expect(result.current.image?.id).toBe("test-image-123");
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("returns undefined when imageId is undefined", () => {
      const { result } = renderHook(() => useImageDetail(undefined), {
        wrapper: createWrapper(),
      });

      expect(result.current.image).toBeUndefined();
    });

    it("computes encodedImageId correctly", () => {
      const { result } = renderHook(
        () => useImageDetail("image/with/slashes"),
        {
          wrapper: createWrapper(),
        }
      );

      expect(result.current.encodedImageId).toBe("image%2Fwith%2Fslashes");
    });

    it("computes filename from path", () => {
      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      expect(result.current.filename).toBe("test-image.fits");
    });

    it("tracks image in recent items when loaded", () => {
      renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      expect(mockAddRecentImage).toHaveBeenCalledWith("test-image-123");
    });
  });

  describe("delete modal", () => {
    it("initially has modal closed", () => {
      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      expect(result.current.deleteState.showModal).toBe(false);
      expect(result.current.deleteState.isDeleting).toBe(false);
      expect(result.current.deleteState.error).toBeNull();
    });

    it("opens delete modal", () => {
      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.openDeleteModal();
      });

      expect(result.current.deleteState.showModal).toBe(true);
    });

    it("closes delete modal", () => {
      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.openDeleteModal();
      });
      expect(result.current.deleteState.showModal).toBe(true);

      act(() => {
        result.current.closeDeleteModal();
      });
      expect(result.current.deleteState.showModal).toBe(false);
    });

    it("clears error when opening modal", () => {
      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      // Simulate an error state
      act(() => {
        result.current.openDeleteModal();
      });

      expect(result.current.deleteState.error).toBeNull();
    });
  });

  describe("delete operation", () => {
    it("calls API and redirects on successful delete", async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({});

      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.confirmDelete();
      });

      expect(apiClient.delete).toHaveBeenCalledWith(
        "/v1/images/test-image-123",
        expect.anything()
      );
      expect(window.location.href).toBe("/images");
    });

    it("sets error state on delete failure", async () => {
      vi.mocked(apiClient.delete).mockRejectedValueOnce(
        new Error("Network error")
      );

      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.confirmDelete();
      });

      expect(result.current.deleteState.error).toBe("Network error");
      expect(result.current.deleteState.isDeleting).toBe(false);
    });

    it("does nothing when imageId is undefined", async () => {
      const { result } = renderHook(() => useImageDetail(undefined), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.confirmDelete();
      });

      expect(apiClient.delete).not.toHaveBeenCalled();
    });
  });

  describe("rating submission", () => {
    it("submits rating and refetches", async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({});

      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.submitRating({
          confidence: "true",
          tagId: "good",
          notes: "Great image",
        });
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        "/v1/images/test-image-123/rating",
        {
          itemId: "test-image-123",
          confidence: "true",
          tagId: "good",
          notes: "Great image",
        }
      );
      expect(mockRefetch).toHaveBeenCalled();
    });

    it("throws on rating failure", async () => {
      const ratingError = new Error("Rating failed");
      vi.mocked(apiClient.post).mockRejectedValueOnce(ratingError);

      const { result } = renderHook(() => useImageDetail("test-image-123"), {
        wrapper: createWrapper(),
      });

      let caughtError: Error | undefined;
      await act(async () => {
        try {
          await result.current.submitRating({
            confidence: "true",
            tagId: "good",
            notes: "",
          });
        } catch (e) {
          caughtError = e as Error;
        }
      });

      expect(caughtError).toBeDefined();
      expect(caughtError?.message).toBe("Rating failed");
    });

    it("does nothing when imageId is undefined", async () => {
      const { result } = renderHook(() => useImageDetail(undefined), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.submitRating({
          confidence: "true",
          tagId: "good",
          notes: "",
        });
      });

      expect(apiClient.post).not.toHaveBeenCalled();
    });
  });
});
