import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from "react";
import * as d3 from "d3";
import { geoAitoff, geoHammer, geoMollweide } from "d3-geo-projection";

/** Projection type options */
type ProjectionType = "aitoff" | "mollweide" | "hammer" | "mercator";

export interface Pointing {
  id: string;
  ra: number; // degrees
  dec: number; // degrees
  radius?: number; // field of view radius in degrees
  label?: string;
  status?: "completed" | "scheduled" | "failed";
  epoch?: string;
}

export interface SkyCoverageMapSimpleProps {
  /** Array of pointing/observation data */
  pointings: Pointing[];
  /** Projection type */
  projection?: ProjectionType;
  /** Width of the map */
  width?: number;
  /** Height of the map */
  height?: number;
  /** Whether to show the galactic plane */
  showGalacticPlane?: boolean;
  /** Whether to show ecliptic */
  showEcliptic?: boolean;
  /** Whether to show the Global Sky Model radio background */
  showRadioBackground?: boolean;
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

/**
 * Convert galactic coordinates (l, b) to equatorial (RA, Dec) in degrees.
 */
function galacticToEquatorial(l: number, b: number): [number, number] {
  const lRad = (l * Math.PI) / 180;
  const bRad = (b * Math.PI) / 180;

  // North Galactic Pole (J2000): RA = 192.85948°, Dec = +27.12825°
  const raGP = (192.85948 * Math.PI) / 180;
  const decGP = (27.12825 * Math.PI) / 180;
  const lAscend = (32.93192 * Math.PI) / 180;

  const sinDec =
    Math.sin(bRad) * Math.sin(decGP) +
    Math.cos(bRad) * Math.cos(decGP) * Math.sin(lRad - lAscend);
  const dec = Math.asin(sinDec);

  const y = Math.cos(bRad) * Math.cos(lRad - lAscend);
  const x =
    Math.sin(bRad) * Math.cos(decGP) -
    Math.cos(bRad) * Math.sin(decGP) * Math.sin(lRad - lAscend);

  let ra = raGP + Math.atan2(y, x);
  ra = ((((ra * 180) / Math.PI) % 360) + 360) % 360;
  const decDeg = (dec * 180) / Math.PI;

  return [ra, decDeg];
}

/**
 * Calculate ecliptic coordinates as equatorial (RA, Dec).
 */
function eclipticToEquatorial(eclipticLon: number): [number, number] {
  const obliquity = 23.4392911;
  const oblRad = (obliquity * Math.PI) / 180;
  const lonRad = (eclipticLon * Math.PI) / 180;

  const sinDec = Math.sin(lonRad) * Math.sin(oblRad);
  const dec = (Math.asin(sinDec) * 180) / Math.PI;

  const y = Math.sin(lonRad) * Math.cos(oblRad);
  const x = Math.cos(lonRad);
  let ra = (Math.atan2(y, x) * 180) / Math.PI;
  ra = ((ra % 360) + 360) % 360;

  return [ra, dec];
}

// Pre-compute coordinate curves
const GALACTIC_PLANE_COORDS = Array.from({ length: 361 }, (_, i) =>
  galacticToEquatorial(i, 0)
);

const ECLIPTIC_COORDS = Array.from({ length: 361 }, (_, i) =>
  eclipticToEquatorial(i)
);

/**
 * Simplified all-sky coverage map focused on DSA-110 pointings.
 * Shows pointings over optional radio sky background (GSM).
 */
const SkyCoverageMapSimple: React.FC<SkyCoverageMapSimpleProps> = ({
  pointings,
  projection = "mollweide",
  width = 800,
  height = 400,
  showGalacticPlane = true,
  showEcliptic = false,
  showRadioBackground = true,
  colorScheme = "status",
  defaultRadius = 1.5,
  onPointingClick,
  onPointingHover,
  className = "",
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedProjection, setSelectedProjection] =
    useState<ProjectionType>(projection);
  const [hoveredPointing, setHoveredPointing] = useState<Pointing | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Get D3 projection
  const getProjection = useCallback(() => {
    const scale = Math.min(width, height * 2) / 6;

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
      .attr("fill", "#0a0a20");

    // Get projection bounds from graticule outline
    const graticuleOutline = d3.geoGraticule().outline();
    const outlineBounds = path.bounds(graticuleOutline);
    const mapX = outlineBounds[0][0];
    const mapY = outlineBounds[0][1];
    const mapWidth = outlineBounds[1][0] - outlineBounds[0][0];
    const mapHeight = outlineBounds[1][1] - outlineBounds[0][1];

    // Create clip path for projection area
    const clipId = `map-clip-${Math.random().toString(36).substr(2, 9)}`;
    svg
      .append("defs")
      .append("clipPath")
      .attr("id", clipId)
      .append("path")
      .datum(graticuleOutline)
      .attr("d", path);

    // Add GSM radio sky background
    if (showRadioBackground && selectedProjection === "mollweide") {
      svg
        .append("image")
        .attr("clip-path", `url(#${clipId})`)
        .attr("href", "/gsm_mollweide.png")
        .attr("x", mapX)
        .attr("y", mapY)
        .attr("width", mapWidth)
        .attr("height", mapHeight)
        .attr("preserveAspectRatio", "none")
        .attr("opacity", 0.7);
    }

    // Graticule (coordinate grid)
    const graticule = d3.geoGraticule().step([30, 15]);
    svg
      .append("path")
      .datum(graticule())
      .attr("d", path)
      .attr("fill", "none")
      .attr("stroke", showRadioBackground ? "#444" : "#333")
      .attr("stroke-width", 0.5)
      .attr("stroke-opacity", 0.6);

    // Graticule outline
    svg
      .append("path")
      .datum(graticuleOutline)
      .attr("d", path)
      .attr("fill", "none")
      .attr("stroke", "#666")
      .attr("stroke-width", 1.5);

    // Galactic plane
    if (showGalacticPlane) {
      const galacticLine = d3
        .line<[number, number]>()
        .x((d) => proj(d)?.[0] ?? 0)
        .y((d) => proj(d)?.[1] ?? 0)
        .defined((d) => proj(d) !== null)
        .curve(d3.curveLinear);

      svg
        .append("path")
        .datum(GALACTIC_PLANE_COORDS as [number, number][])
        .attr("d", galacticLine)
        .attr("fill", "none")
        .attr("stroke", "#ff6b6b")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "5,3")
        .attr("opacity", 0.8);
    }

    // Ecliptic
    if (showEcliptic) {
      const eclipticLine = d3
        .line<[number, number]>()
        .x((d) => proj(d)?.[0] ?? 0)
        .y((d) => proj(d)?.[1] ?? 0)
        .defined((d) => proj(d) !== null)
        .curve(d3.curveLinear);

      svg
        .append("path")
        .datum(ECLIPTIC_COORDS as [number, number][])
        .attr("d", eclipticLine)
        .attr("fill", "none")
        .attr("stroke", "#f0c674")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "3,3")
        .attr("opacity", 0.8);
    }

    // Pointings group
    const pointingsGroup = svg.append("g").attr("class", "pointings");

    // Render all pointings
    pointings.forEach((pointing) => {
      const coords = proj([pointing.ra, pointing.dec]);
      if (!coords) return;

      // Calculate pixel radius
      const radius = pointing.radius ?? defaultRadius;
      const refPoint = proj([pointing.ra + radius, pointing.dec]);
      let pixelRadius = 3;
      if (refPoint) {
        pixelRadius = Math.max(Math.abs(refPoint[0] - coords[0]), 3);
      }

      const group = pointingsGroup
        .append("g")
        .attr("class", "pointing")
        .style("cursor", "pointer");

      // Field of view circle
      group
        .append("circle")
        .attr("cx", coords[0])
        .attr("cy", coords[1])
        .attr("r", Math.max(pixelRadius, 4))
        .attr("fill", getPointingColor(pointing))
        .attr("fill-opacity", 0.4)
        .attr("stroke", getPointingColor(pointing))
        .attr("stroke-width", 1.5)
        .attr("stroke-opacity", 0.9);

      // Center marker
      group
        .append("circle")
        .attr("cx", coords[0])
        .attr("cy", coords[1])
        .attr("r", 2)
        .attr("fill", getPointingColor(pointing));

      // Event handlers
      group
        .on("mouseenter", (event: MouseEvent) => {
          setHoveredPointing(pointing);
          setTooltipPos({ x: event.clientX, y: event.clientY });
          onPointingHover?.(pointing);
          group
            .select("circle")
            .attr("fill-opacity", 0.7)
            .attr("stroke-width", 2.5);
        })
        .on("mouseleave", () => {
          setHoveredPointing(null);
          onPointingHover?.(null);
          group
            .select("circle")
            .attr("fill-opacity", 0.4)
            .attr("stroke-width", 1.5);
        })
        .on("click", () => onPointingClick?.(pointing));
    });

    // Legend (fixed position, doesn't zoom)
    const legend = svg
      .append("g")
      .attr("transform", `translate(${width - 140}, 15)`);

    // Legend background
    let legendHeight = 20;
    if (colorScheme === "status") legendHeight += 50;
    if (showGalacticPlane) legendHeight += 18;
    if (showEcliptic) legendHeight += 18;

    legend
      .append("rect")
      .attr("width", 130)
      .attr("height", legendHeight)
      .attr("fill", "rgba(0,0,0,0.7)")
      .attr("rx", 4);

    let y = 14;

    // Header
    legend
      .append("text")
      .attr("x", 8)
      .attr("y", y)
      .attr("fill", "#fff")
      .attr("font-size", 10)
      .attr("font-weight", "bold")
      .text("DSA-110 Pointings");

    y += 14;

    // Status legend
    if (colorScheme === "status") {
      const statuses = [
        { label: "Good QA", color: "#4fc3a1" },
        { label: "Pending", color: "#f0c674" },
        { label: "Failed QA", color: "#ff6b6b" },
      ];

      statuses.forEach((s) => {
        legend
          .append("circle")
          .attr("cx", 14)
          .attr("cy", y)
          .attr("r", 4)
          .attr("fill", s.color);

        legend
          .append("text")
          .attr("x", 24)
          .attr("y", y + 3)
          .attr("fill", "#ccc")
          .attr("font-size", 9)
          .text(s.label);

        y += 14;
      });

      y += 4;
    }

    // Galactic plane legend
    if (showGalacticPlane) {
      legend
        .append("line")
        .attr("x1", 8)
        .attr("y1", y)
        .attr("x2", 22)
        .attr("y2", y)
        .attr("stroke", "#ff6b6b")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "5,3");

      legend
        .append("text")
        .attr("x", 28)
        .attr("y", y + 3)
        .attr("fill", "#ccc")
        .attr("font-size", 9)
        .text("Galactic plane");

      y += 16;
    }

    // Ecliptic legend
    if (showEcliptic) {
      legend
        .append("line")
        .attr("x1", 8)
        .attr("y1", y)
        .attr("x2", 22)
        .attr("y2", y)
        .attr("stroke", "#f0c674")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "3,3");

      legend
        .append("text")
        .attr("x", 28)
        .attr("y", y + 3)
        .attr("fill", "#ccc")
        .attr("font-size", 9)
        .text("Ecliptic");
    }
  }, [
    pointings,
    selectedProjection,
    width,
    height,
    showGalacticPlane,
    showEcliptic,
    showRadioBackground,
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
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-600">
            Projection:
            <select
              value={selectedProjection}
              onChange={(e) =>
                setSelectedProjection(e.target.value as ProjectionType)
              }
              className="ml-2 px-2 py-1 border border-gray-300 rounded text-sm"
            >
              <option value="mollweide">Mollweide</option>
              <option value="aitoff">Aitoff</option>
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
          style={{ left: tooltipPos.x + 15, top: tooltipPos.y + 15 }}
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
        </div>
      )}
    </div>
  );
};

export default SkyCoverageMapSimple;
