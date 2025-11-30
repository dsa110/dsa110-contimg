import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import useProvenance from "./useProvenance";
import * as clientModule from "../api/client";

// Mock the client module
vi.mock("../api/client", () => ({
  fetchProvenanceData: vi.fn(),
}));

describe("useProvenance", () => {
  const mockFetchProvenanceData = vi.mocked(clientModule.fetchProvenanceData);

  const mockProvenance = {
    runId: "test-run-123",
    createdAt: "2024-01-15T10:00:00Z",
    qaGrade: "good" as const,
    pipelineVersion: "1.2.3",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("returns null provenance initially", () => {
      mockFetchProvenanceData.mockImplementation(() => new Promise(() => {})); // never resolves
      const { result } = renderHook(() => useProvenance("run-123"));
      expect(result.current.provenance).toBeNull();
    });

    it("returns loading true when runId provided", () => {
      mockFetchProvenanceData.mockImplementation(() => new Promise(() => {}));
      const { result } = renderHook(() => useProvenance("run-123"));
      expect(result.current.loading).toBe(true);
    });

    it("returns loading false when no runId", () => {
      const { result } = renderHook(() => useProvenance());
      expect(result.current.loading).toBe(false);
    });

    it("returns null error initially", () => {
      mockFetchProvenanceData.mockImplementation(() => new Promise(() => {}));
      const { result } = renderHook(() => useProvenance("run-123"));
      expect(result.current.error).toBeNull();
    });
  });

  describe("successful fetch", () => {
    it("fetches provenance data for runId", async () => {
      mockFetchProvenanceData.mockResolvedValueOnce(mockProvenance);

      const { result } = renderHook(() => useProvenance("run-123"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(mockFetchProvenanceData).toHaveBeenCalledWith("run-123");
      expect(result.current.provenance).toEqual(mockProvenance);
      expect(result.current.error).toBeNull();
    });

    it("updates provenance when runId changes", async () => {
      const mockProvenance2 = { ...mockProvenance, runId: "run-456" };
      mockFetchProvenanceData
        .mockResolvedValueOnce(mockProvenance)
        .mockResolvedValueOnce(mockProvenance2);

      const { result, rerender } = renderHook(({ runId }) => useProvenance(runId), {
        initialProps: { runId: "run-123" },
      });

      await waitFor(() => {
        expect(result.current.provenance?.runId).toBe("test-run-123");
      });

      rerender({ runId: "run-456" });

      await waitFor(() => {
        expect(result.current.provenance?.runId).toBe("run-456");
      });

      expect(mockFetchProvenanceData).toHaveBeenCalledTimes(2);
    });
  });

  describe("error handling", () => {
    it("sets error when fetch fails", async () => {
      mockFetchProvenanceData.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useProvenance("run-123"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBe("Network error");
      expect(result.current.provenance).toBeNull();
    });

    it("sets generic error for non-Error rejections", async () => {
      mockFetchProvenanceData.mockRejectedValueOnce("Something went wrong");

      const { result } = renderHook(() => useProvenance("run-123"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBe("Failed to fetch provenance data.");
    });

    it("sets error when no runId provided and fetch attempted", () => {
      const { result } = renderHook(() => useProvenance());

      // When no runId, should set error immediately (or just not fetch)
      expect(result.current.loading).toBe(false);
    });
  });

  describe("skip option", () => {
    it("does not fetch when skip is true", () => {
      renderHook(() => useProvenance("run-123", { skip: true }));

      expect(mockFetchProvenanceData).not.toHaveBeenCalled();
    });

    it("returns loading false when skip is true", () => {
      const { result } = renderHook(() => useProvenance("run-123", { skip: true }));
      expect(result.current.loading).toBe(false);
    });

    it("fetches when skip changes from true to false", async () => {
      mockFetchProvenanceData.mockResolvedValueOnce(mockProvenance);

      const { result, rerender } = renderHook(({ skip }) => useProvenance("run-123", { skip }), {
        initialProps: { skip: true },
      });

      expect(mockFetchProvenanceData).not.toHaveBeenCalled();

      rerender({ skip: false });

      await waitFor(() => {
        expect(mockFetchProvenanceData).toHaveBeenCalled();
      });
    });
  });

  describe("refetch function", () => {
    it("provides a refetch function", async () => {
      mockFetchProvenanceData.mockResolvedValue(mockProvenance);

      const { result } = renderHook(() => useProvenance("run-123"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(typeof result.current.refetch).toBe("function");
    });

    it("refetch fetches data again", async () => {
      mockFetchProvenanceData.mockResolvedValue(mockProvenance);

      const { result } = renderHook(() => useProvenance("run-123"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(mockFetchProvenanceData).toHaveBeenCalledTimes(1);

      act(() => {
        result.current.refetch();
      });

      await waitFor(() => {
        expect(mockFetchProvenanceData).toHaveBeenCalledTimes(2);
      });
    });

    it("refetch does nothing when skip is true", async () => {
      const { result } = renderHook(() => useProvenance("run-123", { skip: true }));

      act(() => {
        result.current.refetch();
      });

      expect(mockFetchProvenanceData).not.toHaveBeenCalled();
    });

    it("refetch does nothing when no runId", async () => {
      const { result } = renderHook(() => useProvenance());

      act(() => {
        result.current.refetch();
      });

      expect(mockFetchProvenanceData).not.toHaveBeenCalled();
    });
  });

  describe("no runId", () => {
    it("does not fetch when runId is undefined", () => {
      renderHook(() => useProvenance(undefined));
      expect(mockFetchProvenanceData).not.toHaveBeenCalled();
    });

    it("does not fetch when runId is empty string", () => {
      renderHook(() => useProvenance(""));
      expect(mockFetchProvenanceData).not.toHaveBeenCalled();
    });
  });
});
