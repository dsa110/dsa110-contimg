/**
 * Tests for Saved Queries API
 */

import { describe, it, expect } from "vitest";
import {
  serializeFilters,
  parseFilters,
  filtersEqual,
  getFilterSummary,
  getVisibilityLabel,
  getVisibilityIcon,
} from "./savedQueries";
import type { UrlFilterState } from "../hooks/useUrlFilterState";

describe("savedQueries utilities", () => {
  describe("serializeFilters", () => {
    it("serializes empty filters to empty string", () => {
      const filters: UrlFilterState = {};
      expect(serializeFilters(filters)).toBe("");
    });

    it("serializes numeric filters", () => {
      const filters: UrlFilterState = {
        ra: 180.5,
        dec: -45.2,
        radius: 5,
      };
      const result = serializeFilters(filters);
      expect(result).toContain("ra=180.5");
      expect(result).toContain("dec=-45.2");
      expect(result).toContain("radius=5");
    });

    it("serializes string filters", () => {
      const filters: UrlFilterState = {
        name: "M31",
        tab: "sources",
      };
      const result = serializeFilters(filters);
      expect(result).toContain("name=M31");
      expect(result).toContain("tab=sources");
    });

    it("serializes boolean filters", () => {
      const filters: UrlFilterState = {
        variable: true,
      };
      const result = serializeFilters(filters);
      expect(result).toContain("variable=true");
    });

    it("excludes undefined values", () => {
      const filters: UrlFilterState = {
        ra: 180,
        dec: undefined,
      };
      const result = serializeFilters(filters);
      expect(result).toContain("ra=180");
      expect(result).not.toContain("dec");
    });
  });

  describe("parseFilters", () => {
    it("parses empty string to empty object", () => {
      expect(parseFilters("")).toEqual({});
    });

    it("parses numeric fields", () => {
      const result = parseFilters("ra=180.5&dec=-45.2&radius=5");
      expect(result.ra).toBe(180.5);
      expect(result.dec).toBe(-45.2);
      expect(result.radius).toBe(5);
    });

    it("parses string fields", () => {
      const result = parseFilters("name=M31&tab=sources");
      expect(result.name).toBe("M31");
      expect(result.tab).toBe("sources");
    });

    it("parses boolean fields", () => {
      const result = parseFilters("variable=true");
      expect(result.variable).toBe(true);

      const result2 = parseFilters("variable=false");
      expect(result2.variable).toBe(false);
    });

    it("ignores invalid numeric values", () => {
      const result = parseFilters("ra=invalid");
      expect(result.ra).toBeUndefined();
    });
  });

  describe("serializeFilters and parseFilters round-trip", () => {
    it("round-trips filters correctly", () => {
      const original: UrlFilterState = {
        ra: 180.5,
        dec: -45.2,
        radius: 5,
        minFlux: 0.1,
        maxFlux: 10,
        minImages: 3,
        name: "test",
        tab: "sources",
        variable: true,
      };

      const serialized = serializeFilters(original);
      const parsed = parseFilters(serialized);

      expect(parsed.ra).toBe(original.ra);
      expect(parsed.dec).toBe(original.dec);
      expect(parsed.radius).toBe(original.radius);
      expect(parsed.minFlux).toBe(original.minFlux);
      expect(parsed.maxFlux).toBe(original.maxFlux);
      expect(parsed.minImages).toBe(original.minImages);
      expect(parsed.name).toBe(original.name);
      expect(parsed.tab).toBe(original.tab);
      expect(parsed.variable).toBe(original.variable);
    });
  });

  describe("filtersEqual", () => {
    it("returns true for equal empty filters", () => {
      expect(filtersEqual({}, {})).toBe(true);
    });

    it("returns true for equal non-empty filters", () => {
      const a: UrlFilterState = { ra: 180, dec: -45 };
      const b: UrlFilterState = { ra: 180, dec: -45 };
      expect(filtersEqual(a, b)).toBe(true);
    });

    it("returns false for different values", () => {
      const a: UrlFilterState = { ra: 180 };
      const b: UrlFilterState = { ra: 181 };
      expect(filtersEqual(a, b)).toBe(false);
    });

    it("returns false for different keys", () => {
      const a: UrlFilterState = { ra: 180 };
      const b: UrlFilterState = { dec: 180 };
      expect(filtersEqual(a, b)).toBe(false);
    });

    it("treats undefined as not present", () => {
      const a: UrlFilterState = { ra: 180, dec: undefined };
      const b: UrlFilterState = { ra: 180 };
      expect(filtersEqual(a, b)).toBe(true);
    });
  });

  describe("getFilterSummary", () => {
    it("returns 'No filters' for empty filters", () => {
      expect(getFilterSummary({})).toBe("No filters");
    });

    it("summarizes cone search", () => {
      const filters: UrlFilterState = { ra: 180, dec: 45, radius: 10 };
      const summary = getFilterSummary(filters);
      expect(summary).toContain("Cone:");
      expect(summary).toContain("180.00°");
      expect(summary).toContain("45.00°");
      expect(summary).toContain("r=10°");
    });

    it("summarizes flux range", () => {
      const filters: UrlFilterState = { minFlux: 0.1, maxFlux: 10 };
      const summary = getFilterSummary(filters);
      expect(summary).toContain("Flux:");
      expect(summary).toContain("0.100");
      expect(summary).toContain("10.000");
    });

    it("summarizes minimum images", () => {
      const filters: UrlFilterState = { minImages: 5 };
      const summary = getFilterSummary(filters);
      expect(summary).toContain("≥5 images");
    });

    it("summarizes name filter", () => {
      const filters: UrlFilterState = { name: "M31" };
      const summary = getFilterSummary(filters);
      expect(summary).toContain('Name: "M31"');
    });

    it("summarizes variable flag", () => {
      const filters: UrlFilterState = { variable: true };
      const summary = getFilterSummary(filters);
      expect(summary).toContain("Variable only");
    });

    it("combines multiple filters with bullets", () => {
      const filters: UrlFilterState = { minFlux: 0.1, variable: true };
      const summary = getFilterSummary(filters);
      expect(summary).toContain("•");
    });
  });

  describe("getVisibilityLabel", () => {
    it("returns correct labels", () => {
      expect(getVisibilityLabel("private")).toBe("Private");
      expect(getVisibilityLabel("shared")).toBe("Shared with team");
      expect(getVisibilityLabel("global")).toBe("Public");
    });
  });

  describe("getVisibilityIcon", () => {
    it("returns correct icons", () => {
      expect(getVisibilityIcon("private")).toBe("🔒");
      expect(getVisibilityIcon("shared")).toBe("👥");
      expect(getVisibilityIcon("global")).toBe("🌐");
    });
  });
});
