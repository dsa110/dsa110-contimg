/**
 * Hook for managing filter state in URL search params.
 *
 * This enables shareable/bookmarkable filter configurations
 * and preserves state across navigation.
 */

import { useSearchParams } from "react-router-dom";
import { useMemo, useCallback } from "react";

/**
 * Generic filter state that can be stored in URL.
 */
export interface UrlFilterState {
  // Cone search
  ra?: number;
  dec?: number;
  radius?: number;
  // Flux filters
  minFlux?: number;
  maxFlux?: number;
  // Detection count
  minImages?: number;
  // Text search
  name?: string;
  // UI state
  tab?: string;
  // Variable only flag
  variable?: boolean;
}

/**
 * Parse a URL param value to number, or return undefined.
 */
function parseNumber(value: string | null): number | undefined {
  if (value === null) return undefined;
  const num = Number(value);
  return isNaN(num) ? undefined : num;
}

/**
 * Parse a URL param value to boolean, or return undefined.
 */
function parseBoolean(value: string | null): boolean | undefined {
  if (value === null) return undefined;
  return value === "true";
}

/**
 * Hook for managing filter state in URL search params.
 *
 * @returns Current filter state and setter function
 *
 * @example
 * ```tsx
 * const { filters, setFilters, clearFilters } = useUrlFilterState();
 *
 * // Read filters
 * console.log(filters.ra, filters.minFlux);
 *
 * // Update single filter
 * setFilters({ minFlux: 0.1 });
 *
 * // Update multiple filters
 * setFilters({ ra: 180, dec: 45, radius: 10 });
 *
 * // Clear a filter
 * setFilters({ minFlux: undefined });
 * ```
 */
export function useUrlFilterState() {
  const [searchParams, setSearchParams] = useSearchParams();

  /**
   * Parse current URL params into filter state.
   */
  const filters = useMemo(
    (): UrlFilterState => ({
      ra: parseNumber(searchParams.get("ra")),
      dec: parseNumber(searchParams.get("dec")),
      radius: parseNumber(searchParams.get("radius")),
      minFlux: parseNumber(searchParams.get("minFlux")),
      maxFlux: parseNumber(searchParams.get("maxFlux")),
      minImages: parseNumber(searchParams.get("minImages")),
      name: searchParams.get("name") ?? undefined,
      tab: searchParams.get("tab") ?? undefined,
      variable: parseBoolean(searchParams.get("variable")),
    }),
    [searchParams]
  );

  /**
   * Update filter state in URL.
   * Only updates provided keys, preserves others.
   */
  const setFilters = useCallback(
    (updates: Partial<UrlFilterState>) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);

        Object.entries(updates).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            next.set(key, String(value));
          } else {
            next.delete(key);
          }
        });

        return next;
      });
    },
    [setSearchParams]
  );

  /**
   * Clear all filters from URL.
   */
  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams());
  }, [setSearchParams]);

  /**
   * Check if any filters are active.
   */
  const hasActiveFilters = useMemo(() => {
    return Object.values(filters).some((v) => v !== undefined && v !== null && v !== "");
  }, [filters]);

  return {
    filters,
    setFilters,
    clearFilters,
    hasActiveFilters,
  };
}

export default useUrlFilterState;
