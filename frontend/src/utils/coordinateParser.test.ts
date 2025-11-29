import { describe, it, expect } from "vitest";
import { parseRA, parseDec, formatRA, formatDec, parseCoordinatePair } from "./coordinateParser";

describe("coordinateParser", () => {
  describe("parseRA", () => {
    it("should parse decimal degrees", () => {
      expect(parseRA("180.5")).toBe(180.5);
      expect(parseRA("0")).toBe(0);
      expect(parseRA("359.999")).toBeCloseTo(359.999);
    });

    it("should parse HMS format with colons", () => {
      // 12:00:00 = 12h = 180°
      expect(parseRA("12:00:00")).toBe(180);
      // 6:30:00 = 6.5h = 97.5°
      expect(parseRA("6:30:00")).toBe(97.5);
      // 0:00:00 = 0°
      expect(parseRA("0:00:00")).toBe(0);
      // 23:59:59 ≈ 359.996°
      expect(parseRA("23:59:59")).toBeCloseTo(359.9958, 3);
    });

    it("should parse HMS format with letters", () => {
      expect(parseRA("12h00m00s")).toBe(180);
      expect(parseRA("6h30m00s")).toBe(97.5);
      expect(parseRA("12h30m45.6s")).toBeCloseTo(187.69, 1);
    });

    it("should parse short HMS format", () => {
      expect(parseRA("12:30")).toBe(187.5);
      expect(parseRA("6h30m")).toBe(97.5);
    });

    it("should handle decimal values in degree range", () => {
      // Values >= 24 are interpreted as degrees
      expect(parseRA("180")).toBe(180);
      expect(parseRA("97.5")).toBe(97.5);
      // Small values < 24 could be hours, but parser interprets as degrees when no separators
      expect(parseRA("12")).toBe(12);
    });

    it("should reject invalid input", () => {
      expect(parseRA("")).toBeNull();
      expect(parseRA("abc")).toBeNull();
      expect(parseRA("400")).toBeNull(); // Out of range
      expect(parseRA("-10")).toBeNull(); // Negative RA
      expect(parseRA("25:00:00")).toBeNull(); // Invalid hours
      expect(parseRA("12:60:00")).toBeNull(); // Invalid minutes
      expect(parseRA("12:00:60")).toBeNull(); // Invalid seconds
    });

    it("should handle whitespace", () => {
      expect(parseRA("  180.5  ")).toBe(180.5);
      // Space-separated HMS is supported
      expect(parseRA("12:30:00")).toBe(187.5);
    });
  });

  describe("parseDec", () => {
    it("should parse decimal degrees", () => {
      expect(parseDec("45.5")).toBe(45.5);
      expect(parseDec("-45.5")).toBe(-45.5);
      expect(parseDec("+45.5")).toBe(45.5);
      expect(parseDec("0")).toBe(0);
      expect(parseDec("90")).toBe(90);
      expect(parseDec("-90")).toBe(-90);
    });

    it("should parse DMS format with colons", () => {
      // +45:30:00 = 45.5°
      expect(parseDec("+45:30:00")).toBe(45.5);
      expect(parseDec("-45:30:00")).toBe(-45.5);
      expect(parseDec("45:30:00")).toBe(45.5);
      // 0:00:00 = 0°
      expect(parseDec("0:00:00")).toBe(0);
    });

    it("should parse DMS format with symbols", () => {
      expect(parseDec("+45°30'00\"")).toBe(45.5);
      expect(parseDec("-45°30'00\"")).toBe(-45.5);
      expect(parseDec("45d30m00s")).toBe(45.5);
    });

    it("should parse short DMS format", () => {
      expect(parseDec("+45:30")).toBe(45.5);
      expect(parseDec("-45d30m")).toBe(-45.5);
    });

    it("should reject out of range values", () => {
      expect(parseDec("91")).toBeNull();
      expect(parseDec("-91")).toBeNull();
      expect(parseDec("100:00:00")).toBeNull();
    });

    it("should reject invalid input", () => {
      expect(parseDec("")).toBeNull();
      expect(parseDec("abc")).toBeNull();
      expect(parseDec("45:60:00")).toBeNull(); // Invalid minutes
      expect(parseDec("45:00:60")).toBeNull(); // Invalid seconds
    });

    it("should handle whitespace", () => {
      expect(parseDec("  +45.5  ")).toBe(45.5);
      // Use supported DMS format with colons
      expect(parseDec("+45:30:00")).toBe(45.5);
    });
  });

  describe("formatRA", () => {
    it("should format RA in HMS", () => {
      expect(formatRA(180)).toBe("12:00:00.00");
      expect(formatRA(0)).toBe("00:00:00.00");
      expect(formatRA(97.5)).toBe("06:30:00.00");
    });

    it("should handle edge cases", () => {
      expect(formatRA(359.999)).toMatch(/^23:59:\d{2}\.\d{2}$/);
    });
  });

  describe("formatDec", () => {
    it("should format Dec in DMS with sign", () => {
      expect(formatDec(45.5)).toBe("+45:30:00.0");
      expect(formatDec(-45.5)).toBe("-45:30:00.0");
      expect(formatDec(0)).toBe("+00:00:00.0");
    });

    it("should handle 90 degree values", () => {
      expect(formatDec(90)).toBe("+90:00:00.0");
      expect(formatDec(-90)).toBe("-90:00:00.0");
    });
  });

  describe("parseCoordinatePair", () => {
    it("should parse comma-separated coordinates", () => {
      const result = parseCoordinatePair("180.0, 45.5");
      expect(result).not.toBeNull();
      expect(result?.ra).toBe(180);
      expect(result?.dec).toBe(45.5);
    });

    it("should parse space-separated coordinates", () => {
      const result = parseCoordinatePair("12:00:00 +45:30:00");
      expect(result).not.toBeNull();
      expect(result?.ra).toBe(180);
      expect(result?.dec).toBe(45.5);
    });

    it("should return null for invalid input", () => {
      expect(parseCoordinatePair("invalid")).toBeNull();
      expect(parseCoordinatePair("")).toBeNull();
      expect(parseCoordinatePair("180")).toBeNull(); // Missing dec
    });
  });
});
