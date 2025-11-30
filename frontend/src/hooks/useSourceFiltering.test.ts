import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useSourceFiltering } from "./useSourceFiltering";
import type { SourceSummary } from "../types";

describe("useSourceFiltering", () => {
  // Sample source data for testing
  const mockSources: SourceSummary[] = [
    {
      id: "src-1",
      name: "Source Alpha",
      ra_deg: 180.5,
      dec_deg: 45.0,
      peak_flux_jy: 0.05,
      num_images: 5,
      eta: 0.8,
      v: 0.3,
    },
    {
      id: "src-2",
      name: "Source Beta",
      ra_deg: 120.0,
      dec_deg: -30.0,
      peak_flux_jy: 0.15,
      num_images: 10,
      eta: 0.2,
      v: 0.1,
    },
    {
      id: "src-3",
      name: "Source Gamma",
      ra_deg: 181.0,
      dec_deg: 44.5,
      peak_flux_jy: 0.001,
      num_images: 2,
      eta: 3.0,
      v: 0.6,
    },
  ];

  describe("initial state", () => {
    it("returns all sources when no filters applied", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      expect(result.current.filteredSources).toHaveLength(3);
      expect(result.current.totalCount).toBe(3);
      expect(result.current.filteredCount).toBe(3);
      expect(result.current.isFiltered).toBe(false);
    });

    it("returns empty array when sources is undefined", () => {
      const { result } = renderHook(() => useSourceFiltering(undefined));

      expect(result.current.filteredSources).toEqual([]);
      expect(result.current.totalCount).toBe(0);
      expect(result.current.filteredCount).toBe(0);
    });

    it("returns empty array when sources is empty", () => {
      const { result } = renderHook(() => useSourceFiltering([]));

      expect(result.current.filteredSources).toEqual([]);
      expect(result.current.totalCount).toBe(0);
    });
  });

  describe("text search", () => {
    it("filters by name (case-insensitive)", () => {
      const { result } = renderHook(() =>
        useSourceFiltering(mockSources, { name: "alpha" })
      );

      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].name).toBe("Source Alpha");
      expect(result.current.isFiltered).toBe(true);
    });

    it("filters by ID", () => {
      const { result } = renderHook(() =>
        useSourceFiltering(mockSources, { name: "src-2" })
      );

      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].id).toBe("src-2");
    });
  });

  describe("flux filtering", () => {
    it("filters by minimum flux", () => {
      const { result } = renderHook(() =>
        useSourceFiltering(mockSources, { minFlux: 0.1 })
      );

      // Only src-2 has peak_flux_jy > 0.1
      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].id).toBe("src-2");
    });
  });

  describe("detection count filtering", () => {
    it("filters by minimum detections", () => {
      const { result } = renderHook(() =>
        useSourceFiltering(mockSources, { minImages: 5 })
      );

      // src-1 (5) and src-2 (10) have >= 5 images
      expect(result.current.filteredSources).toHaveLength(2);
      expect(result.current.filteredSources.every((s) => (s.num_images ?? 0) >= 5)).toBe(true);
    });
  });

  describe("result properties", () => {
    it("returns correct counts", () => {
      const { result } = renderHook(() =>
        useSourceFiltering(mockSources, { minFlux: 0.01 })
      );

      expect(result.current.totalCount).toBe(3);
      expect(result.current.filteredCount).toBe(2);
      expect(result.current.isFiltered).toBe(true);
    });
  });
});
