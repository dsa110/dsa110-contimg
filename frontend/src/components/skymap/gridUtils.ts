/**
 * Sky Map Grid and Graticule Rendering Utilities
 *
 * This module provides grid, graticule, and overlay rendering functions
 * for astronomical sky maps. Extracted from SkyCoverageMap for maintainability.
 */

import * as d3 from "d3";
import type { ProjectionType } from "./projectionUtils";
import { createProjection, galacticToEquatorial, eclipticToEquatorial } from "./projectionUtils";

/**
 * Style configuration for grid elements
 */
export interface GridStyle {
  stroke?: string;
  strokeWidth?: number;
  strokeOpacity?: number;
  strokeDasharray?: string;
}

/**
 * Create SVG graticule (coordinate grid) for the sky map
 *
 * @param svg - D3 selection for the SVG element
 * @param projection - D3 projection to use
 * @param style - Optional style overrides
 */
export function renderGraticule(
  svg: d3.Selection<SVGGElement, unknown, null, undefined>,
  projection: d3.GeoProjection,
  style?: GridStyle
): void {
  const graticule = d3.geoGraticule().step([30, 30]);

  svg
    .append("path")
    .datum(graticule())
    .attr("class", "graticule")
    .attr("d", d3.geoPath(projection))
    .attr("fill", "none")
    .attr("stroke", style?.stroke ?? "#ddd")
    .attr("stroke-width", style?.strokeWidth ?? 0.5)
    .attr("stroke-opacity", style?.strokeOpacity ?? 0.5);
}

/**
 * Render the galactic plane on the sky map
 *
 * @param svg - D3 selection for the SVG group
 * @param projection - D3 projection to use
 * @param style - Optional style overrides
 */
export function renderGalacticPlane(
  svg: d3.Selection<SVGGElement, unknown, null, undefined>,
  projection: d3.GeoProjection,
  style?: GridStyle
): void {
  // Generate galactic plane path (b = 0)
  const galacticPoints: Array<[number, number]> = [];
  for (let l = 0; l <= 360; l += 1) {
    const [ra, dec] = galacticToEquatorial(l, 0);
    // Convert to D3 longitude convention (-180 to 180)
    const lon = ra > 180 ? ra - 360 : ra;
    galacticPoints.push([lon, dec]);
  }

  const lineGenerator = d3
    .line<[number, number]>()
    .x((d) => {
      const coords = projection(d);
      return coords ? coords[0] : 0;
    })
    .y((d) => {
      const coords = projection(d);
      return coords ? coords[1] : 0;
    })
    .defined((d) => {
      const coords = projection(d);
      return coords !== null;
    });

  svg
    .append("path")
    .datum(galacticPoints)
    .attr("class", "galactic-plane")
    .attr("d", lineGenerator)
    .attr("fill", "none")
    .attr("stroke", style?.stroke ?? "#ff6b6b")
    .attr("stroke-width", style?.strokeWidth ?? 2)
    .attr("stroke-opacity", style?.strokeOpacity ?? 0.7)
    .attr("stroke-dasharray", style?.strokeDasharray ?? "5,5");
}

/**
 * Render the ecliptic on the sky map
 *
 * @param svg - D3 selection for the SVG group
 * @param projection - D3 projection to use
 * @param style - Optional style overrides
 */
export function renderEcliptic(
  svg: d3.Selection<SVGGElement, unknown, null, undefined>,
  projection: d3.GeoProjection,
  style?: GridStyle
): void {
  // Generate ecliptic path
  const eclipticPoints: Array<[number, number]> = [];
  for (let lon = 0; lon <= 360; lon += 1) {
    const [ra, dec] = eclipticToEquatorial(lon);
    // Convert to D3 longitude convention (-180 to 180)
    const d3Lon = ra > 180 ? ra - 360 : ra;
    eclipticPoints.push([d3Lon, dec]);
  }

  const lineGenerator = d3
    .line<[number, number]>()
    .x((d) => {
      const coords = projection(d);
      return coords ? coords[0] : 0;
    })
    .y((d) => {
      const coords = projection(d);
      return coords ? coords[1] : 0;
    })
    .defined((d) => {
      const coords = projection(d);
      return coords !== null;
    });

  svg
    .append("path")
    .datum(eclipticPoints)
    .attr("class", "ecliptic")
    .attr("d", lineGenerator)
    .attr("fill", "none")
    .attr("stroke", style?.stroke ?? "#ffd93d")
    .attr("stroke-width", style?.strokeWidth ?? 2)
    .attr("stroke-opacity", style?.strokeOpacity ?? 0.7)
    .attr("stroke-dasharray", style?.strokeDasharray ?? "3,3");
}

/**
 * Render coordinate labels (RA/Dec) on the map edges
 *
 * @param svg - D3 selection for the SVG group
 * @param projection - D3 projection to use
 * @param width - Map width
 * @param height - Map height
 */
export function renderCoordinateLabels(
  svg: d3.Selection<SVGGElement, unknown, null, undefined>,
  projection: d3.GeoProjection,
  width: number,
  height: number
): void {
  // RA labels at Dec = 0
  for (let ra = 0; ra < 360; ra += 30) {
    const lon = ra > 180 ? ra - 360 : ra;
    const coords = projection([lon, 0]);
    if (coords) {
      svg
        .append("text")
        .attr("class", "ra-label")
        .attr("x", coords[0])
        .attr("y", height / 2 + 15)
        .attr("text-anchor", "middle")
        .attr("font-size", "10px")
        .attr("fill", "#666")
        .text(`${ra}°`);
    }
  }

  // Dec labels at RA = 0
  for (let dec = -60; dec <= 60; dec += 30) {
    const coords = projection([0, dec]);
    if (coords) {
      svg
        .append("text")
        .attr("class", "dec-label")
        .attr("x", width / 2 + 5)
        .attr("y", coords[1])
        .attr("text-anchor", "start")
        .attr("font-size", "10px")
        .attr("fill", "#666")
        .text(`${dec > 0 ? "+" : ""}${dec}°`);
    }
  }
}

/**
 * Render map legend
 *
 * @param svg - D3 selection for the SVG group
 * @param width - Map width
 * @param height - Map height
 * @param options - Legend options
 */
export function renderLegend(
  svg: d3.Selection<SVGGElement, unknown, null, undefined>,
  width: number,
  height: number,
  options: {
    showGalacticPlane?: boolean;
    showEcliptic?: boolean;
    pointingColors?: { status: string; color: string }[];
  }
): void {
  const legend = svg.append("g").attr("class", "legend").attr("transform", `translate(10, 10)`);

  let yOffset = 0;
  const lineHeight = 18;

  if (options.showGalacticPlane) {
    legend
      .append("line")
      .attr("x1", 0)
      .attr("y1", yOffset + 8)
      .attr("x2", 20)
      .attr("y2", yOffset + 8)
      .attr("stroke", "#ff6b6b")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "5,5");

    legend
      .append("text")
      .attr("x", 25)
      .attr("y", yOffset + 12)
      .attr("font-size", "11px")
      .attr("fill", "#333")
      .text("Galactic Plane");

    yOffset += lineHeight;
  }

  if (options.showEcliptic) {
    legend
      .append("line")
      .attr("x1", 0)
      .attr("y1", yOffset + 8)
      .attr("x2", 20)
      .attr("y2", yOffset + 8)
      .attr("stroke", "#ffd93d")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "3,3");

    legend
      .append("text")
      .attr("x", 25)
      .attr("y", yOffset + 12)
      .attr("font-size", "11px")
      .attr("fill", "#333")
      .text("Ecliptic");

    yOffset += lineHeight;
  }

  // Pointing status legend
  if (options.pointingColors) {
    for (const { status, color } of options.pointingColors) {
      legend
        .append("circle")
        .attr("cx", 10)
        .attr("cy", yOffset + 8)
        .attr("r", 5)
        .attr("fill", color);

      legend
        .append("text")
        .attr("x", 25)
        .attr("y", yOffset + 12)
        .attr("font-size", "11px")
        .attr("fill", "#333")
        .text(status.charAt(0).toUpperCase() + status.slice(1));

      yOffset += lineHeight;
    }
  }
}

/**
 * Get color for pointing based on status or epoch
 *
 * @param status - Pointing status
 * @param colorScheme - Color scheme to use
 * @param epochIndex - Optional epoch index for epoch-based coloring
 * @returns Color string
 */
export function getPointingColor(
  status: string | undefined,
  colorScheme: "status" | "epoch" | "uniform",
  epochIndex?: number
): string {
  if (colorScheme === "uniform") {
    return "#4ECDC4";
  }

  if (colorScheme === "epoch" && epochIndex !== undefined) {
    const colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"];
    return colors[epochIndex % colors.length];
  }

  // Status-based coloring
  switch (status) {
    case "completed":
      return "#4ECDC4";
    case "scheduled":
      return "#45B7D1";
    case "failed":
      return "#FF6B6B";
    default:
      return "#888";
  }
}

/**
 * Status colors for the legend
 */
export const STATUS_COLORS = [
  { status: "completed", color: "#4ECDC4" },
  { status: "scheduled", color: "#45B7D1" },
  { status: "failed", color: "#FF6B6B" },
];
