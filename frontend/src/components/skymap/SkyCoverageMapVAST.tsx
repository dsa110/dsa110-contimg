import React, { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { geoMollweide } from "d3-geo-projection";

export interface Pointing {
  id: string;
  ra: number; // degrees
  dec: number; // degrees
  radius?: number; // field of view radius in degrees
  label?: string;
  status?: "completed" | "scheduled" | "failed";
  epoch?: string;
}

export interface SkyCoverageMapVASTProps {
  /** Array of pointing/observation data */
  pointings: Pointing[];
  /** Width of the map */
  width?: number;
  /** Height of the map (excluding legend) */
  height?: number;
  /** Default radius for pointings without radius (degrees) */
  defaultRadius?: number;
  /** Callback when pointing is clicked */
  onPointingClick?: (pointing: Pointing) => void;
  /** Custom class name */
  className?: string;
}

/**
 * Sky coverage map styled like VAST/ASKAP plots.
 * Features:
 * - Grayscale GSM radio sky background
 * - Coordinate labels on edges (RA in cyan, Dec in white)
 * - Legend bar at top
 * - DSA-110 pointings shown as cyan circles
 */
const SkyCoverageMapVAST: React.FC<SkyCoverageMapVASTProps> = ({
  pointings,
  width = 800,
  height = 450,
  defaultRadius = 1.5,
  onPointingClick,
  className = "",
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredPointing, setHoveredPointing] = useState<Pointing | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Legend height
  const legendHeight = 30;
  const mapHeight = height - legendHeight;

  // Margins for coordinate labels
  const margin = { top: 10, right: 30, bottom: 30, left: 30 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = mapHeight - margin.top - margin.bottom;

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Create projection - Mollweide centered at RA=0
    const proj = geoMollweide()
      .scale(innerWidth / 5.5)
      .translate([
        margin.left + innerWidth / 2,
        legendHeight + margin.top + innerHeight / 2,
      ])
      .rotate([0, 0, 0]); // RA increases left to right (standard astronomical convention)

    const path = d3.geoPath(proj);

    // White background
    svg
      .append("rect")
      .attr("width", width)
      .attr("height", height)
      .attr("fill", "white");

    // Get projection bounds
    const graticuleOutline = d3.geoGraticule().outline();
    const outlineBounds = path.bounds(graticuleOutline);
    const mapX = outlineBounds[0][0];
    const mapY = outlineBounds[0][1];
    const mapWidth = outlineBounds[1][0] - outlineBounds[0][0];
    const mapHeight2 = outlineBounds[1][1] - outlineBounds[0][1];

    // Clip path for the projection
    const clipId = `vast-clip-${Math.random().toString(36).substr(2, 9)}`;
    svg
      .append("defs")
      .append("clipPath")
      .attr("id", clipId)
      .append("path")
      .datum(graticuleOutline)
      .attr("d", path);

    // GSM background (grayscale)
    svg
      .append("image")
      .attr("clip-path", `url(#${clipId})`)
      .attr("href", "/gsm_mollweide_gray.png")
      .attr("x", mapX)
      .attr("y", mapY)
      .attr("width", mapWidth)
      .attr("height", mapHeight2)
      .attr("preserveAspectRatio", "none")
      .attr("opacity", 1);

    // Light pink overlay for areas outside DSA-110 coverage (dec < -30 or dec > 90)
    // DSA-110 is at latitude ~37°N, so it can see roughly dec > -53° to dec < 90°
    // But primary coverage is more limited

    // Graticule (coordinate grid)
    const graticule = d3.geoGraticule().step([30, 30]);
    svg
      .append("path")
      .datum(graticule())
      .attr("d", path)
      .attr("fill", "none")
      .attr("stroke", "#666")
      .attr("stroke-width", 0.5)
      .attr("stroke-opacity", 0.7);

    // Outline
    svg
      .append("path")
      .datum(graticuleOutline)
      .attr("d", path)
      .attr("fill", "none")
      .attr("stroke", "#333")
      .attr("stroke-width", 1.5);

    // RA labels (along the equator, in cyan like VAST)
    const raLabels = [150, 120, 90, 60, 30, 0, 330, 300, 270, 240, 210];
    raLabels.forEach((ra) => {
      const coords = proj([ra - 180, 0]); // Shift because our projection is centered at 180
      if (coords) {
        svg
          .append("text")
          .attr("x", coords[0])
          .attr("y", coords[1] + 4)
          .attr("fill", "#00cccc")
          .attr("font-size", 11)
          .attr("font-weight", "500")
          .attr("text-anchor", "middle")
          .text(`${ra}°`);
      }
    });

    // Dec labels (on both sides)
    const decLabels = [60, 30, 0, -30, -60];
    decLabels.forEach((dec) => {
      // Left side
      const leftCoords = proj([-180, dec]);
      if (leftCoords) {
        svg
          .append("text")
          .attr("x", leftCoords[0] - 8)
          .attr("y", leftCoords[1] + 4)
          .attr("fill", "#333")
          .attr("font-size", 10)
          .attr("text-anchor", "end")
          .text(dec >= 0 ? `+${dec}°` : `${dec}°`);
      }
      // Right side
      const rightCoords = proj([180, dec]);
      if (rightCoords) {
        svg
          .append("text")
          .attr("x", rightCoords[0] + 8)
          .attr("y", rightCoords[1] + 4)
          .attr("fill", "#333")
          .attr("font-size", 10)
          .attr("text-anchor", "start")
          .text(dec >= 0 ? `+${dec}°` : `${dec}°`);
      }
    });

    // DSA-110 pointings
    const pointingsGroup = svg.append("g").attr("class", "pointings");

    pointings.forEach((pointing) => {
      // Convert RA to the projection coordinate system
      let ra = pointing.ra;
      if (ra > 180) ra -= 360; // Convert 0-360 to -180 to 180

      const coords = proj([ra, pointing.dec]);
      if (!coords) return;

      // Calculate pixel radius
      const radius = pointing.radius ?? defaultRadius;
      const refPoint = proj([ra + radius, pointing.dec]);
      let pixelRadius = 5;
      if (refPoint) {
        pixelRadius = Math.max(Math.abs(refPoint[0] - coords[0]), 5);
      }

      const group = pointingsGroup
        .append("g")
        .attr("class", "pointing")
        .style("cursor", "pointer");

      // Circle for pointing (cyan like DSA-110 branding)
      group
        .append("circle")
        .attr("cx", coords[0])
        .attr("cy", coords[1])
        .attr("r", pixelRadius)
        .attr("fill", "#00cccc")
        .attr("fill-opacity", 0.4)
        .attr("stroke", "#00cccc")
        .attr("stroke-width", 2);

      // Event handlers
      group
        .on("mouseenter", (event: MouseEvent) => {
          setHoveredPointing(pointing);
          setTooltipPos({ x: event.clientX, y: event.clientY });
          group
            .select("circle")
            .attr("fill-opacity", 0.7)
            .attr("stroke-width", 3);
        })
        .on("mouseleave", () => {
          setHoveredPointing(null);
          group
            .select("circle")
            .attr("fill-opacity", 0.4)
            .attr("stroke-width", 2);
        })
        .on("click", () => onPointingClick?.(pointing));
    });

    // Legend bar at top
    const legend = svg.append("g").attr("class", "legend");

    // Legend background
    legend
      .append("rect")
      .attr("x", 0)
      .attr("y", 0)
      .attr("width", width)
      .attr("height", legendHeight)
      .attr("fill", "#f5f5f5")
      .attr("stroke", "#ddd")
      .attr("stroke-width", 1);

    // Legend items
    const legendItems = [
      { label: "DSA-110", color: "#00cccc", type: "circle" },
    ];

    // Add count
    const totalPointings = pointings.length;

    let xOffset = 20;
    legendItems.forEach((item) => {
      if (item.type === "circle") {
        legend
          .append("circle")
          .attr("cx", xOffset + 6)
          .attr("cy", legendHeight / 2)
          .attr("r", 6)
          .attr("fill", item.color)
          .attr("fill-opacity", 0.5)
          .attr("stroke", item.color)
          .attr("stroke-width", 2);
      }

      legend
        .append("text")
        .attr("x", xOffset + 18)
        .attr("y", legendHeight / 2 + 4)
        .attr("fill", "#333")
        .attr("font-size", 12)
        .attr("font-weight", "500")
        .text(`${item.label} (${totalPointings} pointings)`);

      xOffset += 160;
    });
  }, [
    pointings,
    width,
    height,
    innerWidth,
    innerHeight,
    margin,
    legendHeight,
    defaultRadius,
    onPointingClick,
  ]);

  const formatCoord = (ra: number, dec: number) => {
    const raH = ra / 15;
    const h = Math.floor(raH);
    const m = Math.floor((raH - h) * 60);
    const raStr = `${h}h ${m}m`;

    const sign = dec >= 0 ? "+" : "";
    const d = Math.floor(Math.abs(dec));
    const dm = Math.floor((Math.abs(dec) - d) * 60);
    const decStr = `${sign}${d}° ${dm}'`;

    return `RA: ${raStr}, Dec: ${decStr}`;
  };

  return (
    <div className={`relative ${className}`}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="rounded shadow-sm"
        style={{ background: "white" }}
      />

      {/* Tooltip */}
      {hoveredPointing && (
        <div
          className="fixed bg-white border border-gray-300 rounded shadow-lg p-2 z-50 pointer-events-none text-sm"
          style={{ left: tooltipPos.x + 12, top: tooltipPos.y + 12 }}
        >
          <p className="font-semibold">
            {hoveredPointing.label || hoveredPointing.id}
          </p>
          <p className="text-gray-600 text-xs">
            {formatCoord(hoveredPointing.ra, hoveredPointing.dec)}
          </p>
        </div>
      )}
    </div>
  );
};

export default SkyCoverageMapVAST;
