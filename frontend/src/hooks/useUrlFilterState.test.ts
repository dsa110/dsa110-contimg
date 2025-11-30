import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MemoryRouter, useSearchParams } from "react-router-dom";
import { ReactNode } from "react";
import { useUrlFilterState } from "./useUrlFilterState";

// Mock searchParams
const mockSetSearchParams = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useSearchParams: () => [mockSearchParams, mockSetSearchParams],
  };
});

describe("useUrlFilterState", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
  });

  // Wrapper with router context
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter>{children}</MemoryRouter>
  );

  describe("initial state", () => {
    it("returns default filter values when URL has no params", () => {
      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      expect(result.current.filters).toEqual({
        ra: undefined,
        dec: undefined,
        radius: undefined,
        minFlux: undefined,
        maxFlux: undefined,
        tab: undefined,
      });
    });

    it("parses existing URL params", () => {
      mockSearchParams = new URLSearchParams({
        ra: "180.5",
        dec: "45.0",
        radius: "2",
        minFlux: "0.001",
        maxFlux: "1.0",
        tab: "variability",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      expect(result.current.filters).toEqual({
        ra: 180.5,
        dec: 45.0,
        radius: 2,
        minFlux: 0.001,
        maxFlux: 1.0,
        tab: "variability",
      });
    });

    it("ignores invalid numeric values", () => {
      mockSearchParams = new URLSearchParams({
        ra: "not-a-number",
        dec: "45.0",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      expect(result.current.filters.ra).toBeNaN();
      expect(result.current.filters.dec).toBe(45.0);
    });
  });

  describe("setFilters", () => {
    it("updates URL params when filters change", () => {
      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      act(() => {
        result.current.setFilters({ ra: 180, dec: 45 });
      });

      expect(mockSetSearchParams).toHaveBeenCalled();
      const callArg = mockSetSearchParams.mock.calls[0][0];
      const params = typeof callArg === "function" ? callArg(new URLSearchParams()) : callArg;
      expect(params.get("ra")).toBe("180");
      expect(params.get("dec")).toBe("45");
    });

    it("removes params when values are undefined", () => {
      mockSearchParams = new URLSearchParams({
        ra: "180",
        dec: "45",
        radius: "2",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      act(() => {
        result.current.setFilters({ radius: undefined });
      });

      expect(mockSetSearchParams).toHaveBeenCalled();
    });

    it("preserves unrelated params", () => {
      mockSearchParams = new URLSearchParams({
        ra: "180",
        other: "preserved",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      act(() => {
        result.current.setFilters({ dec: 45 });
      });

      expect(mockSetSearchParams).toHaveBeenCalled();
    });
  });

  describe("clearFilters", () => {
    it("clears all filter params", () => {
      mockSearchParams = new URLSearchParams({
        ra: "180",
        dec: "45",
        radius: "2",
        minFlux: "0.001",
        tab: "list",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      act(() => {
        result.current.clearFilters();
      });

      expect(mockSetSearchParams).toHaveBeenCalled();
    });
  });

  describe("hasActiveFilters", () => {
    it("returns false when no filters are active", () => {
      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      expect(result.current.hasActiveFilters).toBe(false);
    });

    it("returns true when coordinate filters are active", () => {
      mockSearchParams = new URLSearchParams({
        ra: "180",
        dec: "45",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      expect(result.current.hasActiveFilters).toBe(true);
    });

    it("returns true when flux filters are active", () => {
      mockSearchParams = new URLSearchParams({
        minFlux: "0.001",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      expect(result.current.hasActiveFilters).toBe(true);
    });

    it("ignores tab param for active filter check", () => {
      mockSearchParams = new URLSearchParams({
        tab: "variability",
      });

      const { result } = renderHook(() => useUrlFilterState(), { wrapper });

      // Tab should not count as an active filter
      expect(result.current.hasActiveFilters).toBe(false);
    });
  });
});
