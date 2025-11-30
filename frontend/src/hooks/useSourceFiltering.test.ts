import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
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
      mean_flux_jy: 0.05,
      num_images: 5,
      eta_v: 0.8,
      v_mod: 0.3,
    },
    {
      id: "src-2",
      name: "Source Beta",
      ra_deg: 120.0,
      dec_deg: -30.0,
      mean_flux_jy: 0.15,
      num_images: 10,
      eta_v: 0.2,
      v_mod: 0.1,
    },
    {
      id: "src-3",
      name: "Source Gamma",
      ra_deg: 181.0,
      dec_deg: 44.5,
      mean_flux_jy: 0.001,
      num_images: 2,
      eta_v: 1.5,
      v_mod: 0.6,
    },
  ];

  describe("initial state", () => {
    it("returns all sources when no filters applied", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      expect(result.current.filteredSources).toHaveLength(3);
      expect(result.current.filteredSources).toEqual(mockSources);
    });

    it("returns empty array when sources is undefined", () => {
      const { result } = renderHook(() => useSourceFiltering(undefined));

      expect(result.current.filteredSources).toEqual([]);
    });

    it("returns empty array when sources is empty", () => {
      const { result } = renderHook(() => useSourceFiltering([]));

      expect(result.current.filteredSources).toEqual([]);
    });
  });

  describe("text search", () => {
    it("filters by name (case-insensitive)", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setSearchText("alpha");
      });

      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].name).toBe("Source Alpha");
    });

    it("filters by ID", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setSearchText("src-2");
      });

      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].id).toBe("src-2");
    });

    it("returns empty when no match", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setSearchText("nonexistent");
      });

      expect(result.current.filteredSources).toHaveLength(0);
    });
  });

  describe("cone search", () => {
    it("filters by cone search radius", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        // Search centered at src-1 location with small radius
        result.current.setConeSearch({
          ra: 180.5,
          dec: 45.0,
          radiusArcmin: 60, // 1 degree radius
        });
      });

      // Should find src-1 (exact match) and src-3 (nearby)
      expect(result.current.filteredSources.length).toBeGreaterThanOrEqual(1);
      expect(result.current.filteredSources.some((s) => s.id === "src-1")).toBe(true);
    });

    it("clears cone search when set to undefined", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setConeSearch({ ra: 180.5, dec: 45.0, radiusArcmin: 1 });
      });

      act(() => {
        result.current.setConeSearch(undefined);
      });

      expect(result.current.filteredSources).toHaveLength(3);
    });
  });

  describe("flux filtering", () => {
    it("filters by minimum flux", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setFluxRange({ min: 0.1 });
      });

      // Only src-2 has flux > 0.1
      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].id).toBe("src-2");
    });

    it("filters by maximum flux", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setFluxRange({ max: 0.01 });
      });

      // Only src-3 has flux < 0.01
      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].id).toBe("src-3");
    });

    it("filters by flux range", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setFluxRange({ min: 0.01, max: 0.1 });
      });

      // Only src-1 is in range
      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].id).toBe("src-1");
    });
  });

  describe("detection count filtering", () => {
    it("filters by minimum detections", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setMinImages(5);
      });

      // src-1 (5) and src-2 (10) have >= 5 images
      expect(result.current.filteredSources).toHaveLength(2);
      expect(result.current.filteredSources.every((s) => (s.num_images ?? 0) >= 5)).toBe(true);
    });
  });

  describe("variability filtering", () => {
    it("filters by minimum eta_v", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setVariabilityThresholds({ minEtaV: 0.5 });
      });

      // src-1 (0.8) and src-3 (1.5) have eta_v > 0.5
      expect(result.current.filteredSources).toHaveLength(2);
    });

    it("filters by minimum v_mod", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setVariabilityThresholds({ minVMod: 0.5 });
      });

      // Only src-3 has v_mod > 0.5
      expect(result.current.filteredSources).toHaveLength(1);
      expect(result.current.filteredSources[0].id).toBe("src-3");
    });
  });

  describe("combined filters", () => {
    it("applies multiple filters together", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setSearchText("Source");
        result.current.setFluxRange({ min: 0.01 });
        result.current.setMinImages(3);
      });

      // After all filters: name matches all 3, flux excludes src-3, minImages excludes src-3
      // Result should be src-1 and src-2
      expect(result.current.filteredSources).toHaveLength(2);
      expect(result.current.filteredSources.some((s) => s.id === "src-1")).toBe(true);
      expect(result.current.filteredSources.some((s) => s.id === "src-2")).toBe(true);
    });
  });

  describe("clearAllFilters", () => {
    it("resets all filters to initial state", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      // Apply various filters
      act(() => {
        result.current.setSearchText("Alpha");
        result.current.setFluxRange({ min: 0.1 });
        result.current.setMinImages(5);
      });

      // Clear all
      act(() => {
        result.current.clearAllFilters();
      });

      expect(result.current.filteredSources).toHaveLength(3);
      expect(result.current.searchText).toBe("");
      expect(result.current.fluxRange).toBeUndefined();
      expect(result.current.minImages).toBeUndefined();
    });
  });

  describe("activeFilterCount", () => {
    it("returns 0 when no filters active", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      expect(result.current.activeFilterCount).toBe(0);
    });

    it("counts each active filter type", () => {
      const { result } = renderHook(() => useSourceFiltering(mockSources));

      act(() => {
        result.current.setSearchText("test");
        result.current.setFluxRange({ min: 0.01 });
        result.current.setMinImages(3);
        result.current.setConeSearch({ ra: 180, dec: 45, radiusArcmin: 10 });
      });

      expect(result.current.activeFilterCount).toBe(4);
    });
  });
});
