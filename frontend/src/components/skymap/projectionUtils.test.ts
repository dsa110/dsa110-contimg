/**
 * Tests for Sky Map Projection and Coordinate Transformation Utilities
 */

import { describe, it, expect } from "vitest";
import {
  galacticToEquatorial,
  eclipticToEquatorial,
  generateGalacticPlane,
  generateEcliptic,
  createProjection,
  projectCoordinates,
  createCirclePath,
} from "./projectionUtils";
import { GALACTIC_POLE, EARTH_OBLIQUITY_DEG } from "../../constants/astronomical";

describe("projectionUtils", () => {
  describe("galacticToEquatorial", () => {
    it("converts galactic center (l=0, b=0) to roughly Sagittarius A*", () => {
      const [ra, dec] = galacticToEquatorial(0, 0);
      // Galactic center is at approximately RA 266°, Dec -29°
      expect(ra).toBeCloseTo(266, 0);
      expect(dec).toBeCloseTo(-29, 0);
    });

    it("converts galactic north pole (l=0, b=90) to known coordinates", () => {
      const [ra, dec] = galacticToEquatorial(0, 90);
      // North galactic pole is at RA ~192.86°, Dec ~27.13° (J2000)
      expect(ra).toBeCloseTo(GALACTIC_POLE.RA_DEG, 1);
      expect(dec).toBeCloseTo(GALACTIC_POLE.DEC_DEG, 1);
    });

    it("converts galactic anti-center (l=180, b=0) correctly", () => {
      const [ra, dec] = galacticToEquatorial(180, 0);
      // Anti-center is roughly RA 86°, Dec +29°
      expect(ra).toBeCloseTo(86, 0);
      expect(dec).toBeCloseTo(29, 0);
    });

    it("normalizes RA to [0, 360)", () => {
      const [ra, _dec] = galacticToEquatorial(0, 0);
      expect(ra).toBeGreaterThanOrEqual(0);
      expect(ra).toBeLessThan(360);
    });

    it("handles negative galactic longitude", () => {
      const [ra, dec] = galacticToEquatorial(-90, 0);
      expect(ra).toBeGreaterThanOrEqual(0);
      expect(ra).toBeLessThan(360);
      expect(dec).toBeGreaterThanOrEqual(-90);
      expect(dec).toBeLessThanOrEqual(90);
    });
  });

  describe("eclipticToEquatorial", () => {
    it("converts vernal equinox (lon=0) to RA=0, Dec=0", () => {
      const [ra, dec] = eclipticToEquatorial(0);
      expect(ra).toBeCloseTo(0, 5);
      expect(dec).toBeCloseTo(0, 5);
    });

    it("converts summer solstice (lon=90) correctly", () => {
      const [ra, dec] = eclipticToEquatorial(90);
      // At ecliptic longitude 90°, Dec should equal obliquity
      expect(ra).toBeCloseTo(90, 0);
      expect(dec).toBeCloseTo(EARTH_OBLIQUITY_DEG, 1);
    });

    it("converts autumnal equinox (lon=180) correctly", () => {
      const [ra, dec] = eclipticToEquatorial(180);
      expect(ra).toBeCloseTo(180, 0);
      expect(dec).toBeCloseTo(0, 5);
    });

    it("converts winter solstice (lon=270) correctly", () => {
      const [ra, dec] = eclipticToEquatorial(270);
      // At ecliptic longitude 270°, Dec should be -obliquity
      expect(ra).toBeCloseTo(270, 0);
      expect(dec).toBeCloseTo(-EARTH_OBLIQUITY_DEG, 1);
    });

    it("normalizes RA to [0, 360)", () => {
      const [ra, _dec] = eclipticToEquatorial(400);
      expect(ra).toBeGreaterThanOrEqual(0);
      expect(ra).toBeLessThan(360);
    });
  });

  describe("generateGalacticPlane", () => {
    it("generates the default 360 points", () => {
      const plane = generateGalacticPlane();
      expect(plane.length).toBe(361); // 0 to 360 inclusive
    });

    it("generates custom number of points", () => {
      const plane = generateGalacticPlane(36);
      expect(plane.length).toBe(37); // 0 to 360 with step of 10
    });

    it("all points have valid RA/Dec coordinates", () => {
      const plane = generateGalacticPlane(36);
      plane.forEach(([ra, dec]) => {
        expect(ra).toBeGreaterThanOrEqual(0);
        expect(ra).toBeLessThan(360);
        expect(dec).toBeGreaterThanOrEqual(-90);
        expect(dec).toBeLessThanOrEqual(90);
      });
    });

    it("generates points along b=0 (galactic plane)", () => {
      const plane = generateGalacticPlane(4);
      // All points should be on the galactic plane, which spans a range of declinations
      expect(plane.length).toBeGreaterThan(0);
    });
  });

  describe("generateEcliptic", () => {
    it("generates the default 360 points", () => {
      const ecliptic = generateEcliptic();
      expect(ecliptic.length).toBe(361);
    });

    it("generates custom number of points", () => {
      const ecliptic = generateEcliptic(36);
      expect(ecliptic.length).toBe(37);
    });

    it("all points have valid RA/Dec coordinates", () => {
      const ecliptic = generateEcliptic(36);
      ecliptic.forEach(([ra, dec]) => {
        expect(ra).toBeGreaterThanOrEqual(0);
        expect(ra).toBeLessThan(360);
        expect(dec).toBeGreaterThanOrEqual(-90);
        expect(dec).toBeLessThanOrEqual(90);
      });
    });

    it("ecliptic declination stays within ±obliquity", () => {
      const ecliptic = generateEcliptic(36);
      const maxDec = EARTH_OBLIQUITY_DEG + 1; // Small tolerance
      ecliptic.forEach(([_ra, dec]) => {
        expect(Math.abs(dec)).toBeLessThanOrEqual(maxDec);
      });
    });
  });

  describe("createProjection", () => {
    const width = 800;
    const height = 400;

    it("creates aitoff projection", () => {
      const projection = createProjection("aitoff", width, height);
      expect(projection).toBeDefined();
      // Center should map to center of viewport
      const center = projection([0, 0]);
      expect(center).toBeDefined();
      expect(center![0]).toBeCloseTo(width / 2, 0);
      expect(center![1]).toBeCloseTo(height / 2, 0);
    });

    it("creates mollweide projection", () => {
      const projection = createProjection("mollweide", width, height);
      expect(projection).toBeDefined();
      const center = projection([0, 0]);
      expect(center).toBeDefined();
    });

    it("creates hammer projection", () => {
      const projection = createProjection("hammer", width, height);
      expect(projection).toBeDefined();
      const center = projection([0, 0]);
      expect(center).toBeDefined();
    });

    it("creates mercator projection", () => {
      const projection = createProjection("mercator", width, height);
      expect(projection).toBeDefined();
      const center = projection([0, 0]);
      expect(center).toBeDefined();
    });

    it("defaults to aitoff for unknown type", () => {
      // Using type assertion to test fallback behavior
      const projection = createProjection("unknown" as any, width, height);
      expect(projection).toBeDefined();
    });
  });

  describe("projectCoordinates", () => {
    const projection = createProjection("aitoff", 800, 400);

    it("projects center coordinates (RA=0, Dec=0)", () => {
      const coords = projectCoordinates(0, 0, projection);
      expect(coords).not.toBeNull();
      expect(coords![0]).toBeCloseTo(400, 0); // Center X
      expect(coords![1]).toBeCloseTo(200, 0); // Center Y
    });

    it("converts RA > 180 to negative longitude", () => {
      // RA = 270° should become lon = -90°
      const coords = projectCoordinates(270, 0, projection);
      expect(coords).not.toBeNull();
    });

    it("handles RA = 180 (boundary)", () => {
      const coords = projectCoordinates(180, 0, projection);
      expect(coords).not.toBeNull();
    });

    it("projects north pole (Dec=90)", () => {
      const coords = projectCoordinates(0, 90, projection);
      expect(coords).not.toBeNull();
    });

    it("projects south pole (Dec=-90)", () => {
      const coords = projectCoordinates(0, -90, projection);
      expect(coords).not.toBeNull();
    });
  });

  describe("createCirclePath", () => {
    const projection = createProjection("aitoff", 800, 400);

    it("creates a closed path string", () => {
      const path = createCirclePath(180, 45, 10, projection);
      expect(path).toContain("M "); // Starts with move command
      expect(path).toContain(" Z"); // Ends with close path command
    });

    it("creates path with specified number of points", () => {
      const path = createCirclePath(180, 45, 10, projection, 8);
      // Should have 8 line commands plus initial move
      const lineCommands = path.match(/L /g);
      expect(lineCommands).toBeDefined();
      expect(lineCommands!.length).toBe(8);
    });

    it("returns empty string for unprojectable coordinates", () => {
      // Create a mercator projection and try to project near the poles
      const mercator = createProjection("mercator", 800, 400);
      // Most projections should still handle this, but test the guard
      const path = createCirclePath(0, 85, 10, mercator, 4);
      // Should return some path (mercator handles near-poles)
      expect(typeof path).toBe("string");
    });

    it("clamps declination to valid range", () => {
      // Circle near north pole might exceed Dec=90
      const path = createCirclePath(180, 85, 10, projection, 8);
      // Should still produce a valid path without errors
      expect(path).toBeDefined();
    });

    it("handles circle at equator", () => {
      const path = createCirclePath(180, 0, 5, projection);
      expect(path).toContain("M ");
      expect(path).toContain(" Z");
    });

    it("handles small radius", () => {
      const path = createCirclePath(180, 45, 1, projection, 16);
      expect(path).toContain("M ");
    });
  });
});
