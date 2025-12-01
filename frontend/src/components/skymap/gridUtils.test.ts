/**
 * Tests for Sky Map Grid and Graticule Rendering Utilities
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import * as d3 from "d3";
import { JSDOM } from "jsdom";
import {
  getPointingColor,
  STATUS_COLORS,
  renderGraticule,
  renderGalacticPlane,
  renderEcliptic,
  renderCoordinateLabels,
  renderLegend,
} from "./gridUtils";
import { createProjection } from "./projectionUtils";

// Setup JSDOM for D3 tests
function createSvgGroup(): d3.Selection<SVGGElement, unknown, null, undefined> {
  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
  const document = dom.window.document;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(group);
  document.body.appendChild(svg);
  return d3.select(group) as d3.Selection<SVGGElement, unknown, null, undefined>;
}

describe("gridUtils", () => {
  describe("getPointingColor", () => {
    describe("uniform color scheme", () => {
      it("returns uniform color regardless of status", () => {
        expect(getPointingColor("completed", "uniform")).toBe("#4ECDC4");
        expect(getPointingColor("failed", "uniform")).toBe("#4ECDC4");
        expect(getPointingColor(undefined, "uniform")).toBe("#4ECDC4");
      });
    });

    describe("epoch color scheme", () => {
      it("returns color based on epoch index", () => {
        const color0 = getPointingColor("any", "epoch", 0);
        const color1 = getPointingColor("any", "epoch", 1);
        const color2 = getPointingColor("any", "epoch", 2);

        expect(color0).toBe("#FF6B6B");
        expect(color1).toBe("#4ECDC4");
        expect(color2).toBe("#45B7D1");
      });

      it("cycles through colors for large epoch indices", () => {
        const colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"];

        for (let i = 0; i < 12; i++) {
          expect(getPointingColor("any", "epoch", i)).toBe(colors[i % 6]);
        }
      });

      it("falls back to status coloring when epochIndex is undefined", () => {
        // Without epochIndex, it should use status-based coloring
        expect(getPointingColor("completed", "epoch", undefined)).toBe("#4ECDC4");
      });
    });

    describe("status color scheme", () => {
      it("returns correct color for completed status", () => {
        expect(getPointingColor("completed", "status")).toBe("#4ECDC4");
      });

      it("returns correct color for scheduled status", () => {
        expect(getPointingColor("scheduled", "status")).toBe("#45B7D1");
      });

      it("returns correct color for failed status", () => {
        expect(getPointingColor("failed", "status")).toBe("#FF6B6B");
      });

      it("returns default color for unknown status", () => {
        expect(getPointingColor("unknown", "status")).toBe("#888");
        expect(getPointingColor("pending", "status")).toBe("#888");
      });

      it("returns default color for undefined status", () => {
        expect(getPointingColor(undefined, "status")).toBe("#888");
      });
    });
  });

  describe("STATUS_COLORS", () => {
    it("contains expected status entries", () => {
      expect(STATUS_COLORS).toHaveLength(3);
      expect(STATUS_COLORS).toContainEqual({ status: "completed", color: "#4ECDC4" });
      expect(STATUS_COLORS).toContainEqual({ status: "scheduled", color: "#45B7D1" });
      expect(STATUS_COLORS).toContainEqual({ status: "failed", color: "#FF6B6B" });
    });

    it("colors match getPointingColor status scheme", () => {
      for (const { status, color } of STATUS_COLORS) {
        expect(getPointingColor(status, "status")).toBe(color);
      }
    });
  });

  describe("renderGraticule", () => {
    it("renders a graticule path element", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderGraticule(svg, projection);

      const path = svg.select("path.graticule");
      expect(path.empty()).toBe(false);
    });

    it("applies default style when no style provided", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderGraticule(svg, projection);

      const path = svg.select("path.graticule");
      expect(path.attr("fill")).toBe("none");
      expect(path.attr("stroke")).toBe("#ddd");
      expect(path.attr("stroke-width")).toBe("0.5");
    });

    it("applies custom style overrides", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderGraticule(svg, projection, {
        stroke: "#999",
        strokeWidth: 1,
        strokeOpacity: 0.8,
      });

      const path = svg.select("path.graticule");
      expect(path.attr("stroke")).toBe("#999");
      expect(path.attr("stroke-width")).toBe("1");
      expect(path.attr("stroke-opacity")).toBe("0.8");
    });
  });

  describe("renderGalacticPlane", () => {
    it("renders a galactic plane path element", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderGalacticPlane(svg, projection);

      const path = svg.select("path.galactic-plane");
      expect(path.empty()).toBe(false);
    });

    it("applies default galactic plane style", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderGalacticPlane(svg, projection);

      const path = svg.select("path.galactic-plane");
      expect(path.attr("stroke")).toBe("#ff6b6b");
      expect(path.attr("stroke-width")).toBe("2");
      expect(path.attr("stroke-dasharray")).toBe("5,5");
    });

    it("applies custom style overrides", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderGalacticPlane(svg, projection, {
        stroke: "#00ff00",
        strokeWidth: 3,
      });

      const path = svg.select("path.galactic-plane");
      expect(path.attr("stroke")).toBe("#00ff00");
      expect(path.attr("stroke-width")).toBe("3");
    });
  });

  describe("renderEcliptic", () => {
    it("renders an ecliptic path element", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderEcliptic(svg, projection);

      const path = svg.select("path.ecliptic");
      expect(path.empty()).toBe(false);
    });

    it("applies default ecliptic style", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderEcliptic(svg, projection);

      const path = svg.select("path.ecliptic");
      expect(path.attr("stroke")).toBe("#ffd93d");
      expect(path.attr("stroke-width")).toBe("2");
      expect(path.attr("stroke-dasharray")).toBe("3,3");
    });
  });

  describe("renderCoordinateLabels", () => {
    it("renders RA labels at regular intervals", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderCoordinateLabels(svg, projection, 800, 400);

      const raLabels = svg.selectAll("text.ra-label");
      // Should have labels at 0°, 30°, 60°, ..., 330°
      expect(raLabels.size()).toBeGreaterThan(0);
    });

    it("renders Dec labels at regular intervals", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderCoordinateLabels(svg, projection, 800, 400);

      const decLabels = svg.selectAll("text.dec-label");
      // Should have labels at -60°, -30°, 0°, 30°, 60°
      expect(decLabels.size()).toBeGreaterThan(0);
    });

    it("formats Dec labels with +/- prefix", () => {
      const svg = createSvgGroup();
      const projection = createProjection("aitoff", 800, 400);

      renderCoordinateLabels(svg, projection, 800, 400);

      const decLabels = svg.selectAll("text.dec-label");
      const labels: string[] = [];
      decLabels.each(function () {
        labels.push(d3.select(this).text());
      });

      // Positive declinations should have + prefix
      expect(labels.some((l) => l.startsWith("+"))).toBe(true);
      // Negative declinations should have - prefix
      expect(labels.some((l) => l.startsWith("-"))).toBe(true);
    });
  });

  describe("renderLegend", () => {
    it("renders legend group", () => {
      const svg = createSvgGroup();

      renderLegend(svg, 800, 400, {});

      const legend = svg.select("g.legend");
      expect(legend.empty()).toBe(false);
    });

    it("renders galactic plane legend item when enabled", () => {
      const svg = createSvgGroup();

      renderLegend(svg, 800, 400, { showGalacticPlane: true });

      const legendText = svg.selectAll("g.legend text");
      let hasGalacticPlane = false;
      legendText.each(function () {
        if (d3.select(this).text() === "Galactic Plane") {
          hasGalacticPlane = true;
        }
      });
      expect(hasGalacticPlane).toBe(true);
    });

    it("renders ecliptic legend item when enabled", () => {
      const svg = createSvgGroup();

      renderLegend(svg, 800, 400, { showEcliptic: true });

      const legendText = svg.selectAll("g.legend text");
      let hasEcliptic = false;
      legendText.each(function () {
        if (d3.select(this).text() === "Ecliptic") {
          hasEcliptic = true;
        }
      });
      expect(hasEcliptic).toBe(true);
    });

    it("renders pointing colors legend items", () => {
      const svg = createSvgGroup();

      renderLegend(svg, 800, 400, {
        pointingColors: [
          { status: "completed", color: "#4ECDC4" },
          { status: "failed", color: "#FF6B6B" },
        ],
      });

      const circles = svg.selectAll("g.legend circle");
      expect(circles.size()).toBe(2);
    });

    it("capitalizes status text in legend", () => {
      const svg = createSvgGroup();

      renderLegend(svg, 800, 400, {
        pointingColors: [{ status: "completed", color: "#4ECDC4" }],
      });

      const legendText = svg.selectAll("g.legend text");
      let hasCapitalized = false;
      legendText.each(function () {
        if (d3.select(this).text() === "Completed") {
          hasCapitalized = true;
        }
      });
      expect(hasCapitalized).toBe(true);
    });
  });
});
