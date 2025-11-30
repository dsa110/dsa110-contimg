/**
 * Hook for filtering source data.
 *
 * Centralizes all source filtering logic to keep components clean.
 */

import { useMemo } from "react";
import type { SourceSummary } from "../types";

/**
 * Cone search parameters.
 */
export interface ConeSearchParams {
  ra?: number;
  dec?: number;
  radius?: number; // arcminutes
}

/**
 * Flux filter parameters.
 */
export interface FluxFilterParams {
  minFlux?: number;
  maxFlux?: number;
}

/**
 * Advanced filter parameters.
 */
export interface AdvancedFilterParams {
  name?: string;
  minImages?: number;
  variableOnly?: boolean;
}

/**
 * Combined filter options.
 */
export interface SourceFilterOptions
  extends ConeSearchParams,
    FluxFilterParams,
    AdvancedFilterParams {}

/**
 * Calculate angular distance between two points (simplified).
 * Uses small-angle approximation suitable for nearby sources.
 *
 * @param ra1 RA of first point (degrees)
 * @param dec1 Dec of first point (degrees)
 * @param ra2 RA of second point (degrees)
 * @param dec2 Dec of second point (degrees)
 * @returns Distance in arcminutes
 */
function angularDistance(ra1: number, dec1: number, ra2: number, dec2: number): number {
  // Small-angle approximation
  const dRa = (ra2 - ra1) * Math.cos((dec1 * Math.PI) / 180);
  const dDec = dec2 - dec1;
  return Math.sqrt(dRa * dRa + dDec * dDec) * 60; // Convert to arcminutes
}

/**
 * Hook for filtering source data.
 *
 * @param sources Source data array
 * @param options Filter options
 * @returns Filtered sources and metadata
 *
 * @example
 * ```tsx
 * const { filteredSources, totalCount, filteredCount } = useSourceFiltering(
 *   sources,
 *   { ra: 180, dec: 45, radius: 10, minFlux: 0.1, variableOnly: true }
 * );
 * ```
 */
export function useSourceFiltering(
  sources: SourceSummary[] | undefined,
  options: SourceFilterOptions = {}
) {
  const { ra, dec, radius, minFlux, maxFlux, name, minImages, variableOnly } = options;

  const result = useMemo(() => {
    if (!sources) {
      return {
        filteredSources: [],
        totalCount: 0,
        filteredCount: 0,
        isFiltered: false,
      };
    }

    let filtered = [...sources];

    // Apply cone search filter
    if (ra !== undefined && dec !== undefined && radius !== undefined && radius > 0) {
      filtered = filtered.filter((s) => {
        if (s.ra_deg === undefined || s.dec_deg === undefined) return false;
        const dist = angularDistance(ra, dec, s.ra_deg, s.dec_deg);
        return dist <= radius;
      });
    }

    // Apply flux filters
    if (minFlux !== undefined) {
      filtered = filtered.filter((s) => (s.peak_flux_jy ?? 0) >= minFlux);
    }
    if (maxFlux !== undefined) {
      filtered = filtered.filter((s) => (s.peak_flux_jy ?? Infinity) <= maxFlux);
    }

    // Apply name search
    if (name && name.trim()) {
      const term = name.toLowerCase().trim();
      filtered = filtered.filter(
        (s) => s.name?.toLowerCase().includes(term) || s.id.toLowerCase().includes(term)
      );
    }

    // Apply minimum images filter
    if (minImages !== undefined && minImages > 0) {
      filtered = filtered.filter((s) => (s.num_images ?? 0) >= minImages);
    }

    // Apply variable-only filter
    if (variableOnly) {
      filtered = filtered.filter(
        (s) => s.eta !== undefined && s.v !== undefined && (s.eta > 2 || s.v > 0.1)
      );
    }

    return {
      filteredSources: filtered,
      totalCount: sources.length,
      filteredCount: filtered.length,
      isFiltered: filtered.length !== sources.length,
    };
  }, [sources, ra, dec, radius, minFlux, maxFlux, name, minImages, variableOnly]);

  return result;
}

export default useSourceFiltering;
