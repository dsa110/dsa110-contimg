import React, { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { geoAitoff, geoHammer, geoMollweide } from "d3-geo-projection";

export interface Pointing {
  id: string;
  ra: number; // degrees
  dec: number; // degrees
  radius?: number; // field of view radius in degrees
  label?: string;
  status?: "completed" | "scheduled" | "failed";
  epoch?: string;
}

export interface SkyCoverageMapProps {
  /** Array of pointing/observation data */
  pointings: Pointing[];
  /** Projection type */
  projection?: "aitoff" | "mollweide" | "hammer" | "mercator";
  /** Width of the map */
  width?: number;
  /** Height of the map */
  height?: number;
  /** Whether to show the galactic plane */
  showGalacticPlane?: boolean;
  /** Whether to show ecliptic */
  showEcliptic?: boolean;
  /** Whether to show constellation boundaries */
  showConstellations?: boolean;
  /** Color scheme for pointings */
  colorScheme?: "status" | "epoch" | "uniform";
  /** Default radius for pointings without radius (degrees) */
  defaultRadius?: number;
  /** Callback when pointing is clicked */
  onPointingClick?: (pointing: Pointing) => void;
  /** Callback when pointing is hovered */
  onPointingHover?: (pointing: Pointing | null) => void;
  /** Custom class name */
  className?: string;
}

// Galactic plane coordinates (approximate)
const GALACTIC_PLANE_COORDS = Array.from({ length: 361 }, (_, i) => {
  const l = i; // galactic longitude
  // Convert galactic to equatorial (simplified approximation)
  const lRad = (l * Math.PI) / 180;
  const ra = (192.85 + l) % 360;
  const dec = 27.13 * Math.sin(lRad - (33 * Math.PI) / 180);
  return [ra, dec];
});

// Ecliptic coordinates
const ECLIPTIC_COORDS = Array.from({ length: 361 }, (_, i) => {
  const lon = i;
  const obliquity = 23.44; // Earth's axial tilt
  const ra = lon;
  const dec = obliquity * Math.sin((lon * Math.PI) / 180);
  return [ra, dec];
});

/**
 * All-sky coverage map with D3.js celestial projections.
 */
const SkyCoverageMap: React.FC<SkyCoverageMapProps> = ({
  pointings,
  projection = "aitoff",
  width = 800,
  height = 400,
  showGalacticPlane = true,
  showEcliptic = false,
  showConstellations = false,
  colorScheme = "status",
  defaultRadius = 1.5,
  onPointingClick,
  onPointingHover,
  className = "",
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedProjection, setSelectedProjection] = useState(projection);
  const [hoveredPointing, setHoveredPointing] = useState<Pointing | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Get D3 projection
  const getProjection = useCallback(() => {
    const scale = Math.min(width, height * 2) / 6;
    const center: [number, number] = [0, 0];

    switch (selectedProjection) {
      case "mollweide":
        return geoMollweide()
          .scale(scale * 1.4)
          .translate([width / 2, height / 2])
          .rotate([-180, 0, 0]);
      case "hammer":
        return geoHammer()
          .scale(scale * 1.4)
          .translate([width / 2, height / 2])
          .rotate([-180, 0, 0]);
      case "mercator":
        return d3
          .geoMercator()
          .scale(scale * 0.8)
          .translate([width / 2, height / 2])
          .rotate([-180, 0, 0]);
      case "aitoff":
      default:
        return geoAitoff()
          .scale(scale * 1.4)
          .translate([width / 2, height / 2])
          .rotate([-180, 0, 0]);
    }
  }, [selectedProjection, width, height]);

  // Color scale for pointings
  const getPointingColor = useCallback(
    (pointing: Pointing) => {
      if (colorScheme === "uniform") return "#4fc3a1";

      if (colorScheme === "status") {
        switch (pointing.status) {
          case "completed":
            return "#4fc3a1";
          case "scheduled":
            return "#f0c674";
          case "failed":
            return "#ff6b6b";
          default:
            return "#4fc3a1";
        }
      }

      // Epoch-based coloring (hash epoch to color)
      if (colorScheme === "epoch" && pointing.epoch) {
        const hash = pointing.epoch.split("").reduce((a, b) => {
          a = (a << 5) - a + b.charCodeAt(0);
          return a & a;
        }, 0);
        return d3.interpolateRainbow(Math.abs(hash % 100) / 100);
      }

      return "#4fc3a1";
    },
    [colorScheme]
  );

  // Render map
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const proj = getProjection();
    const path = d3.geoPath(proj);

    // Background
    svg
      .append("rect")
      .attr("width", width)
      .attr("height", height)
      .attr("fill", "#1a1a2e");

    // Graticule (coordinate grid)
    const graticule = d3.geoGraticule().step([30, 15]);
    svg
      .append("path")
      .datum(graticule())
      .attr("d", path)
      .attr("fill", "none")
      .attr("stroke", "#333")
      .attr("stroke-width", 0.5)
      .attr("stroke-opacity", 0.5);

    // Graticule outline
    svg
      .append("path")
      .datum(graticule.outline())
      .attr("d", path)
      .attr("fill", "none")
      .attr("stroke", "#555")
      .attr("stroke-width", 1);

    // Galactic plane
    if (showGalacticPlane) {
      const galacticLine = d3
        .line<[number, number]>()
        .x((d) => {
          const p = proj(d);
          return p ? p[0] : 0;
        })
        .y((d) => {
          const p = proj(d);
          return p ? p[1] : 0;
        })
        .defined((d) => {
          const p = proj(d);
          return p !== null;
        })
        .curve(d3.curveCardinal);

      svg
        .append("path")
        .datum(GALACTIC_PLANE_COORDS as [number, number][])
        .attr("d", galacticLine)
        .attr("fill", "none")
        .attr("stroke", "#ff6b6b")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "5,3")
        .attr("opacity", 0.7);
    }

    // Ecliptic
    if (showEcliptic) {
      const eclipticLine = d3
        .line<[number, number]>()
        .x((d) => {
          const p = proj(d);
          return p ? p[0] : 0;
        })
        .y((d) => {
          const p = proj(d);
          return p ? p[1] : 0;
        })
        .defined((d) => {
          const p = proj(d);
          return p !== null;
        })
        .curve(d3.curveCardinal);

      svg
        .append("path")
        .datum(ECLIPTIC_COORDS as [number, number][])
        .attr("d", eclipticLine)
        .attr("fill", "none")
        .attr("stroke", "#f0c674")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "3,3")
        .attr("opacity", 0.7);
    }

    // RA/Dec labels
    const raLabels = [0, 3, 6, 9, 12, 15, 18, 21];
    raLabels.forEach((ra) => {
      const coords = proj([ra * 15, 0]);
      if (coords) {
        svg
          .append("text")
          .attr("x", coords[0])
          .attr("y", height - 10)
          .attr("text-anchor", "middle")
          .attr("fill", "#888")
          .attr("font-size", 10)
          .text(`${ra}h`);
      }
    });

    const decLabels = [-60, -30, 0, 30, 60];
    decLabels.forEach((dec) => {
      const coords = proj([180, dec]);
      if (coords && coords[0] > 0 && coords[0] < width) {
        svg
          .append("text")
          .attr("x", 10)
          .attr("y", coords[1])
          .attr("fill", "#888")
          .attr("font-size", 10)
          .text(`${dec}°`);
      }
    });

    // Pointings
    const pointingGroup = svg.append("g").attr("class", "pointings");

    pointings.forEach((pointing) => {
      const coords = proj([pointing.ra, pointing.dec]);
      if (!coords) return;

      const radius = pointing.radius ?? defaultRadius;
      // Convert degree radius to pixel radius (approximate)
      const pixelRadius = (radius / 180) * Math.min(width, height);

      const group = pointingGroup
        .append("g")
        .attr("class", "pointing")
        .attr("cursor", "pointer");

      // Field of view circle
      group
        .append("circle")
        .attr("cx", coords[0])
        .attr("cy", coords[1])
        .attr("r", Math.max(pixelRadius, 3))
        .attr("fill", getPointingColor(pointing))
        .attr("fill-opacity", 0.3)
        .attr("stroke", getPointingColor(pointing))
        .attr("stroke-width", 1.5)
        .attr("stroke-opacity", 0.8);

      // Center marker
      group
        .append("circle")
        .attr("cx", coords[0])
        .attr("cy", coords[1])
        .attr("r", 2)
        .attr("fill", getPointingColor(pointing));

      // Event handlers
      group
        .on("mouseenter", (event) => {
          setHoveredPointing(pointing);
          setTooltipPos({ x: event.clientX, y: event.clientY });
          onPointingHover?.(pointing);

          // Highlight
          group.select("circle").attr("fill-opacity", 0.6).attr("stroke-width", 2.5);
        })
        .on("mouseleave", () => {
          setHoveredPointing(null);
          onPointingHover?.(null);

          // Remove highlight
          group.select("circle").attr("fill-opacity", 0.3).attr("stroke-width", 1.5);
        })
        .on("click", () => {
          onPointingClick?.(pointing);
        });
    });

    // Legend
    const legend = svg.append("g").attr("transform", `translate(${width - 120}, 20)`);

    legend
      .append("rect")
      .attr("width", 110)
      .attr("height", showGalacticPlane && showEcliptic ? 90 : showGalacticPlane || showEcliptic ? 70 : 50)
      .attr("fill", "rgba(0,0,0,0.5)")
      .attr("rx", 4);

    let legendY = 15;

    if (colorScheme === "status") {
      const statuses = [
        { label: "Completed", color: "#4fc3a1" },
        { label: "Scheduled", color: "#f0c674" },
        { label: "Failed", color: "#ff6b6b" },
      ];

      statuses.forEach((s, i) => {
        legend
          .append("circle")
          .attr("cx", 15)
          .attr("cy", legendY + i * 15)
          .attr("r", 5)
          .attr("fill", s.color);

        legend
          .append("text")
          .attr("x", 28)
          .attr("y", legendY + i * 15 + 4)
          .attr("fill", "#ccc")
          .attr("font-size", 10)
          .text(s.label);
      });

      legendY += 45;
    }

    if (showGalacticPlane) {
      legend
        .append("line")
        .attr("x1", 8)
        .attr("y1", legendY)
        .attr("x2", 22)
        .attr("y2", legendY)
        .attr("stroke", "#ff6b6b")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "5,3");

      legend
        .append("text")
        .attr("x", 28)
        .attr("y", legendY + 4)
        .attr("fill", "#ccc")
        .attr("font-size", 10)
        .text("Galactic plane");

      legendY += 15;
    }

    if (showEcliptic) {
      legend
        .append("line")
        .attr("x1", 8)
        .attr("y1", legendY)
        .attr("x2", 22)
        .attr("y2", legendY)
        .attr("stroke", "#f0c674")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "3,3");

      legend
        .append("text")
        .attr("x", 28)
        .attr("y", legendY + 4)
        .attr("fill", "#ccc")
        .attr("font-size", 10)
        .text("Ecliptic");
    }
  }, [
    pointings,
    selectedProjection,
    width,
    height,
    showGalacticPlane,
    showEcliptic,
    colorScheme,
    defaultRadius,
    getProjection,
    getPointingColor,
    onPointingClick,
    onPointingHover,
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

    return `${raStr}, ${decStr}`;
  };

  return (
    <div className={`relative ${className}`}>
      {/* Controls */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-600">
            Projection:
            <select
              value={selectedProjection}
              onChange={(e) => setSelectedProjection(e.target.value as any)}
              className="ml-2 px-2 py-1 border border-gray-300 rounded text-sm"
            >
              <option value="aitoff">Aitoff</option>
              <option value="mollweide">Mollweide</option>
              <option value="hammer">Hammer</option>
              <option value="mercator">Mercator</option>
            </select>
          </label>
        </div>

        <div className="text-sm text-gray-500">
          {pointings.length} pointings
        </div>
      </div>

      {/* SVG Map */}
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="rounded-lg shadow-md"
      />

      {/* Tooltip */}
      {hoveredPointing && (
        <div
          className="fixed bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 pointer-events-none"
          style={{
            left: tooltipPos.x + 15,
            top: tooltipPos.y + 15,
          }}
        >
          <p className="font-semibold text-sm">
            {hoveredPointing.label || hoveredPointing.id}
          </p>
          <p className="text-xs text-gray-500">
            {formatCoord(hoveredPointing.ra, hoveredPointing.dec)}
          </p>
          {hoveredPointing.status && (
            <p className="text-xs mt-1">
              Status:{" "}
              <span
                className={`font-medium ${
                  hoveredPointing.status === "completed"
                    ? "text-green-600"
                    : hoveredPointing.status === "scheduled"
                    ? "text-yellow-600"
                    : "text-red-600"
                }`}
              >
                {hoveredPointing.status}
              </span>
            </p>
          )}
          {hoveredPointing.epoch && (
            <p className="text-xs text-gray-400">Epoch: {hoveredPointing.epoch}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default SkyCoverageMap;
