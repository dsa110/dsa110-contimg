/**
 * Tests for useUrlFilterState hook.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import React from "react";
import { useUrlFilterState } from "./useUrlFilterState";

// Wrapper with MemoryRouter for useSearchParams
const createWrapper = (initialEntries: string[] = ["/"]) => {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(MemoryRouter, { initialEntries }, children);
};

describe("useUrlFilterState", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("returns empty filters when URL has no params", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(),
      });

      expect(result.current.filters).toEqual({
        ra: undefined,
        dec: undefined,
        radius: undefined,
        minFlux: undefined,
        maxFlux: undefined,
        minImages: undefined,
        name: undefined,
        tab: undefined,
        variable: undefined,
      });
      expect(result.current.hasActiveFilters).toBe(false);
    });

    it("parses numeric params from URL", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?ra=180&dec=45&radius=10"]),
      });

      expect(result.current.filters.ra).toBe(180);
      expect(result.current.filters.dec).toBe(45);
      expect(result.current.filters.radius).toBe(10);
      expect(result.current.hasActiveFilters).toBe(true);
    });

    it("parses string params from URL", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?name=test&tab=variability"]),
      });

      expect(result.current.filters.name).toBe("test");
      expect(result.current.filters.tab).toBe("variability");
    });

    it("parses boolean params from URL", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?variable=true"]),
      });

      expect(result.current.filters.variable).toBe(true);
    });

    it("handles invalid numeric values gracefully", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?ra=invalid&dec=45"]),
      });

      expect(result.current.filters.ra).toBeUndefined();
      expect(result.current.filters.dec).toBe(45);
    });
  });

  describe("setFilters", () => {
    it("updates single filter", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFilters({ minFlux: 0.1 });
      });

      expect(result.current.filters.minFlux).toBe(0.1);
      expect(result.current.hasActiveFilters).toBe(true);
    });

    it("updates multiple filters at once", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFilters({ ra: 180, dec: 45, radius: 10 });
      });

      expect(result.current.filters.ra).toBe(180);
      expect(result.current.filters.dec).toBe(45);
      expect(result.current.filters.radius).toBe(10);
    });

    it("clears filter when set to undefined", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?minFlux=0.1"]),
      });

      expect(result.current.filters.minFlux).toBe(0.1);

      act(() => {
        result.current.setFilters({ minFlux: undefined });
      });

      expect(result.current.filters.minFlux).toBeUndefined();
    });

    it("preserves other filters when updating one", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?ra=180&dec=45"]),
      });

      act(() => {
        result.current.setFilters({ radius: 10 });
      });

      expect(result.current.filters.ra).toBe(180);
      expect(result.current.filters.dec).toBe(45);
      expect(result.current.filters.radius).toBe(10);
    });
  });

  describe("clearFilters", () => {
    it("clears all filters", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?ra=180&dec=45&minFlux=0.1&name=test"]),
      });

      expect(result.current.hasActiveFilters).toBe(true);

      act(() => {
        result.current.clearFilters();
      });

      expect(result.current.filters.ra).toBeUndefined();
      expect(result.current.filters.dec).toBeUndefined();
      expect(result.current.filters.minFlux).toBeUndefined();
      expect(result.current.filters.name).toBeUndefined();
      expect(result.current.hasActiveFilters).toBe(false);
    });
  });

  describe("hasActiveFilters", () => {
    it("returns false when no filters are set", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(),
      });

      expect(result.current.hasActiveFilters).toBe(false);
    });

    it("returns true when any filter is set", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?minFlux=0.1"]),
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });

    it("returns true for boolean filter set to true", () => {
      const { result } = renderHook(() => useUrlFilterState(), {
        wrapper: createWrapper(["/?variable=true"]),
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });
  });
});
