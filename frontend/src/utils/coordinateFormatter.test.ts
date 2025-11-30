import { describe, it, expect } from "vitest";
import { formatRA, formatDec, formatCoordinates, formatDegrees } from "./coordinateFormatter";

describe("coordinateFormatter", () => {
  describe("formatRA", () => {
    it("formats 0 degrees as 00h 00m 00.00s", () => {
      expect(formatRA(0)).toBe("00h 00m 00.00s");
    });

    it("formats 180 degrees as 12h 00m 00.00s", () => {
      expect(formatRA(180)).toBe("12h 00m 00.00s");
    });

    it("formats 360 degrees (wraps to 0)", () => {
      // 360 degrees = 24 hours, which should display as 24h 00m 00.00s
      // (or could wrap to 00h depending on implementation)
      const result = formatRA(360);
      expect(result).toMatch(/^(24|00)h 00m 00\.00s$/);
    });

    it("formats 90 degrees as 06h 00m 00.00s", () => {
      expect(formatRA(90)).toBe("06h 00m 00.00s");
    });

    it("formats 270 degrees as 18h 00m 00.00s", () => {
      expect(formatRA(270)).toBe("18h 00m 00.00s");
    });

    it("formats fractional degrees correctly", () => {
      // 83.63308 degrees = 5.575539 hours = 5h 34m 31.94s
      const result = formatRA(83.63308);
      expect(result).toMatch(/^05h 34m 31\.\d+s$/);
    });

    it("respects precision parameter", () => {
      const result = formatRA(83.63308, 4);
      expect(result).toMatch(/^05h 34m 31\.\d{4}s$/);
    });

    it("formats with 0 precision", () => {
      const result = formatRA(45, 0);
      expect(result).toBe("03h 00m 00s");
    });

    it("handles negative values (should still work)", () => {
      // Negative RA isn't standard but formatter should handle it
      const result = formatRA(-15);
      expect(result).toBeDefined();
    });
  });

  describe("formatDec", () => {
    it("formats 0 degrees as +00° 00′ 00.0″", () => {
      expect(formatDec(0)).toBe("+00° 00′ 00.0″");
    });

    it("formats +90 degrees (north pole)", () => {
      expect(formatDec(90)).toBe("+90° 00′ 00.0″");
    });

    it("formats -90 degrees (south pole)", () => {
      expect(formatDec(-90)).toBe("-90° 00′ 00.0″");
    });

    it("formats positive declination with + sign", () => {
      const result = formatDec(45.5);
      expect(result).toMatch(/^\+45° 30′/);
    });

    it("formats negative declination with - sign", () => {
      const result = formatDec(-45.5);
      expect(result).toMatch(/^-45° 30′/);
    });

    it("formats fractional degrees correctly", () => {
      // 22.0145 degrees = 22° 00' 52.2"
      const result = formatDec(22.0145);
      expect(result).toMatch(/^\+22° 00′ 52\.\d″$/);
    });

    it("respects precision parameter", () => {
      const result = formatDec(22.0145, 2);
      expect(result).toMatch(/^\+22° 00′ 52\.\d{2}″$/);
    });

    it("formats with 0 precision", () => {
      const result = formatDec(45, 0);
      expect(result).toBe("+45° 00′ 00″");
    });

    it("handles very small negative values", () => {
      const result = formatDec(-0.5);
      expect(result).toMatch(/^-00° 30′/);
    });
  });

  describe("formatCoordinates", () => {
    it("formats both RA and Dec together", () => {
      const result = formatCoordinates(0, 0);
      expect(result).toContain("00h 00m");
      expect(result).toContain("+00°");
    });

    it("separates RA and Dec with comma", () => {
      const result = formatCoordinates(180, 45);
      expect(result).toContain(", ");
    });

    it("formats common astronomical coordinates", () => {
      // Crab Nebula approximate: RA 83.63, Dec 22.01
      const result = formatCoordinates(83.63, 22.01);
      expect(result).toMatch(/05h 34m.*\+22°/);
    });
  });

  describe("formatDegrees", () => {
    it("formats integer with default precision", () => {
      expect(formatDegrees(45)).toBe("45.0000°");
    });

    it("formats decimal with default precision", () => {
      expect(formatDegrees(83.63308)).toBe("83.6331°");
    });

    it("respects custom precision", () => {
      expect(formatDegrees(83.63308, 2)).toBe("83.63°");
      expect(formatDegrees(83.63308, 6)).toBe("83.633080°");
    });

    it("formats 0 precision as integer", () => {
      expect(formatDegrees(45.7, 0)).toBe("46°");
    });

    it("handles negative values", () => {
      expect(formatDegrees(-45.5, 2)).toBe("-45.50°");
    });

    it("handles zero", () => {
      expect(formatDegrees(0, 2)).toBe("0.00°");
    });
  });
});
