import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
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

/** Constellation display options */
export interface ConstellationOptions {
  /** Show constellation names (IAU abbreviations) */
  names?: boolean;
  /** Show constellation lines (stick figures connecting stars) */
  lines?: boolean;
  /** Show IAU constellation boundaries */
  bounds?: boolean;
  /** Line style */
  lineStyle?: { stroke?: string; width?: number; opacity?: number };
  /** Boundary style */
  boundStyle?: { stroke?: string; width?: number; opacity?: number; dash?: string };
  /** Name style */
  nameStyle?: { fill?: string; fontSize?: number; opacity?: number };
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
  /** Whether to show constellations (true = names only for backwards compat, or pass options object) */
  showConstellations?: boolean | ConstellationOptions;
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

// Types for d3-celestial data files
interface ConstellationFeature {
  type: "Feature";
  id: string;
  properties: {
    name: string;
    desig: string;
    rank: string;
    display?: [number, number, number];
  };
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
}

interface ConstellationLinesFeature {
  type: "Feature";
  id: string;
  properties: { rank: string };
  geometry: {
    type: "MultiLineString";
    coordinates: number[][][];
  };
}

interface ConstellationBoundsFeature {
  type: "Feature";
  id: string;
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][] | number[][][][];
  };
}

interface GeoJSONCollection<T> {
  type: "FeatureCollection";
  features: T[];
}

/**
 * Convert galactic coordinates (l, b) to equatorial (RA, Dec) in degrees.
 * Uses the standard IAU transformation.
 */
function galacticToEquatorial(l: number, b: number): [number, number] {
  const lRad = (l * Math.PI) / 180;
  const bRad = (b * Math.PI) / 180;

  // North Galactic Pole (J2000): RA = 192.85948°, Dec = +27.12825°
  const raGP = (192.85948 * Math.PI) / 180;
  const decGP = (27.12825 * Math.PI) / 180;
  // Galactic longitude of ascending node: 32.93192°
  const lAscend = (32.93192 * Math.PI) / 180;

  const sinDec =
    Math.sin(bRad) * Math.sin(decGP) + Math.cos(bRad) * Math.cos(decGP) * Math.sin(lRad - lAscend);
  const dec = Math.asin(sinDec);

  const y = Math.cos(bRad) * Math.cos(lRad - lAscend);
  const x =
    Math.sin(bRad) * Math.cos(decGP) - Math.cos(bRad) * Math.sin(decGP) * Math.sin(lRad - lAscend);

  let ra = raGP + Math.atan2(y, x);

  // Normalize RA to [0, 360)
  ra = ((((ra * 180) / Math.PI) % 360) + 360) % 360;
  const decDeg = (dec * 180) / Math.PI;

  return [ra, decDeg];
}

/**
 * Calculate ecliptic coordinates as equatorial (RA, Dec).
 * The ecliptic is the Sun's apparent path through the sky.
 */
function eclipticToEquatorial(eclipticLon: number): [number, number] {
  const obliquity = 23.4392911; // Earth's axial tilt in degrees (J2000)
  const oblRad = (obliquity * Math.PI) / 180;
  const lonRad = (eclipticLon * Math.PI) / 180;

  // Convert from ecliptic to equatorial
  const sinDec = Math.sin(lonRad) * Math.sin(oblRad);
  const dec = (Math.asin(sinDec) * 180) / Math.PI;

  const y = Math.sin(lonRad) * Math.cos(oblRad);
  const x = Math.cos(lonRad);
  let ra = (Math.atan2(y, x) * 180) / Math.PI;

  // Normalize RA to [0, 360)
  ra = ((ra % 360) + 360) % 360;

  return [ra, dec];
}

// Galactic plane coordinates (b=0 for all galactic longitudes)
const GALACTIC_PLANE_COORDS = Array.from({ length: 361 }, (_, i) => {
  return galacticToEquatorial(i, 0);
});

// Ecliptic coordinates
const ECLIPTIC_COORDS = Array.from({ length: 361 }, (_, i) => {
  return eclipticToEquatorial(i);
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

  // Constellation data state (loaded from d3-celestial JSON files)
  const [constellationNames, setConstellationNames] =
    useState<GeoJSONCollection<ConstellationFeature> | null>(null);
  const [constellationLines, setConstellationLines] =
    useState<GeoJSONCollection<ConstellationLinesFeature> | null>(null);
  const [constellationBounds, setConstellationBounds] =
    useState<GeoJSONCollection<ConstellationBoundsFeature> | null>(null);
  const [constellationLoadError, setConstellationLoadError] = useState<string | null>(null);
  const [isLoadingConstellations, setIsLoadingConstellations] = useState(false);

  // Memoize constellation options to prevent unnecessary re-renders
  const constOptions = useMemo<ConstellationOptions>(() => {
    if (typeof showConstellations === "object") {
      return showConstellations;
    }
    return showConstellations
      ? { names: true, lines: true, bounds: true }
      : { names: false, lines: false, bounds: false };
  }, [showConstellations]);

  // Load constellation data from d3-celestial JSON files
  useEffect(() => {
    const needsNames = constOptions.names && !constellationNames;
    const needsLines = constOptions.lines && !constellationLines;
    const needsBounds = constOptions.bounds && !constellationBounds;

    if (!needsNames && !needsLines && !needsBounds) return;

    let isCancelled = false;
    setIsLoadingConstellations(true);
    setConstellationLoadError(null);

    const loadData = async () => {
      try {
        const fetchPromises: Promise<void>[] = [];

        if (needsNames) {
          fetchPromises.push(
            fetch("/celestial-data/constellations.json")
              .then((resp) => {
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                return resp.json();
              })
              .then((data) => {
                if (!isCancelled) setConstellationNames(data);
              })
          );
        }
        if (needsLines) {
          fetchPromises.push(
            fetch("/celestial-data/constellations.lines.json")
              .then((resp) => {
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                return resp.json();
              })
              .then((data) => {
                if (!isCancelled) setConstellationLines(data);
              })
          );
        }
        if (needsBounds) {
          fetchPromises.push(
            fetch("/celestial-data/constellations.bounds.json")
              .then((resp) => {
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                return resp.json();
              })
              .then((data) => {
                if (!isCancelled) setConstellationBounds(data);
              })
          );
        }

        await Promise.all(fetchPromises);
      } catch (err) {
        if (!isCancelled) {
          const message = err instanceof Error ? err.message : "Unknown error";
          setConstellationLoadError(`Failed to load constellation data: ${message}`);
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingConstellations(false);
        }
      }
    };

    loadData();

    return () => {
      isCancelled = true;
    };
  }, [
    constOptions.names,
    constOptions.lines,
    constOptions.bounds,
    constellationNames,
    constellationLines,
    constellationBounds,
  ]);

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
    svg.append("rect").attr("width", width).attr("height", height).attr("fill", "#1a1a2e");

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
        .curve(d3.curveLinear); // Use linear interpolation for coordinate lines

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
        .curve(d3.curveLinear); // Use linear interpolation for coordinate lines

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

    // Constellation labels (simplified - major constellations at approximate centers)
    // Convert d3-celestial coordinates to our projection format
    // d3-celestial uses [lon, lat] where lon can be negative (west of prime meridian)
    const convertCelestialCoord = (lon: number, lat: number): [number, number] => {
      // Convert from d3-celestial format to standard RA/Dec
      // d3-celestial uses -180 to 180 longitude, we use 0-360 RA
      let ra = lon;
      if (ra < 0) ra += 360;
      return [ra, lat];
    };

    // Render constellation boundaries (behind lines and names)
    if (constOptions.bounds && constellationBounds) {
      const boundStyle = constOptions.boundStyle || {
        stroke: "#666633",
        width: 0.5,
        opacity: 0.4,
        dash: "2,4",
      };

      const boundsGroup = svg.append("g").attr("class", "constellation-bounds");

      constellationBounds.features.forEach((feature) => {
        if (feature.geometry.type === "Polygon") {
          const coords = feature.geometry.coordinates[0] as number[][];
          const pathData = coords
            .map((coord, i) => {
              const [lon, lat] = coord;
              const converted = convertCelestialCoord(lon, lat);
              const projected = proj(converted);
              if (!projected) return null;
              return `${i === 0 ? "M" : "L"}${projected[0]},${projected[1]}`;
            })
            .filter(Boolean)
            .join(" ");

          if (pathData) {
            boundsGroup
              .append("path")
              .attr("d", pathData)
              .attr("fill", "none")
              .attr("stroke", boundStyle.stroke)
              .attr("stroke-width", boundStyle.width)
              .attr("stroke-opacity", boundStyle.opacity)
              .attr("stroke-dasharray", boundStyle.dash);
          }
        }
      });
    }

    // Render constellation lines (stick figures)
    if (constOptions.lines && constellationLines) {
      const lineStyle = constOptions.lineStyle || {
        stroke: "#4a4a6a",
        width: 1,
        opacity: 0.5,
      };

      const linesGroup = svg.append("g").attr("class", "constellation-lines");

      constellationLines.features.forEach((feature) => {
        feature.geometry.coordinates.forEach((lineSegment) => {
          // Each lineSegment is an array of [lon, lat] points
          const pathData = lineSegment
            .map((coord, i) => {
              const [lon, lat] = coord;
              const converted = convertCelestialCoord(lon, lat);
              const projected = proj(converted);
              if (!projected) return null;
              return `${i === 0 ? "M" : "L"}${projected[0]},${projected[1]}`;
            })
            .filter(Boolean)
            .join(" ");

          if (pathData) {
            linesGroup
              .append("path")
              .attr("d", pathData)
              .attr("fill", "none")
              .attr("stroke", lineStyle.stroke)
              .attr("stroke-width", lineStyle.width)
              .attr("stroke-opacity", lineStyle.opacity);
          }
        });
      });
    }

    // Render constellation names
    if (constOptions.names && constellationNames) {
      const nameStyle = constOptions.nameStyle || {
        fill: "#888888",
        fontSize: 10,
        opacity: 0.7,
      };

      const namesGroup = svg.append("g").attr("class", "constellation-names");

      constellationNames.features.forEach((feature) => {
        const [lon, lat] = feature.geometry.coordinates;
        const converted = convertCelestialCoord(lon, lat);
        const coords = proj(converted);

        // Only render if within visible area
        if (
          coords &&
          coords[0] > 30 &&
          coords[0] < width - 30 &&
          coords[1] > 20 &&
          coords[1] < height - 20
        ) {
          // Font size based on constellation rank (1 = major, 3 = minor)
          const rank = parseInt(feature.properties.rank) || 2;
          const fontSize = nameStyle.fontSize - (rank - 1) * 2;

          namesGroup
            .append("text")
            .attr("x", coords[0])
            .attr("y", coords[1])
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", nameStyle.fill)
            .attr("font-size", fontSize)
            .attr("font-style", "italic")
            .attr("opacity", nameStyle.opacity)
            .text(feature.properties.desig); // Use 3-letter abbreviation
        }
      });
    } else if (showConstellations === true) {
      // Fallback to hardcoded list if JSON not loaded yet
      const constellations = [
        { name: "UMa", ra: 165, dec: 55 },
        { name: "UMi", ra: 225, dec: 75 },
        { name: "Cas", ra: 15, dec: 60 },
        { name: "Cyg", ra: 310, dec: 42 },
        { name: "Lyr", ra: 285, dec: 35 },
        { name: "Aql", ra: 295, dec: 5 },
        { name: "Ori", ra: 85, dec: 5 },
        { name: "CMa", ra: 105, dec: -20 },
        { name: "Sgr", ra: 285, dec: -30 },
        { name: "Sco", ra: 255, dec: -30 },
        { name: "Leo", ra: 165, dec: 15 },
        { name: "Vir", ra: 200, dec: -5 },
        { name: "Cen", ra: 200, dec: -45 },
        { name: "Cru", ra: 190, dec: -60 },
        { name: "Car", ra: 130, dec: -60 },
        { name: "Peg", ra: 345, dec: 20 },
        { name: "And", ra: 10, dec: 38 },
        { name: "Per", ra: 55, dec: 45 },
        { name: "Tau", ra: 65, dec: 18 },
        { name: "Gem", ra: 110, dec: 25 },
      ];

      const constGroup = svg.append("g").attr("class", "constellations");

      constellations.forEach(({ name, ra, dec }) => {
        const coords = proj([ra, dec]);
        if (
          coords &&
          coords[0] > 20 &&
          coords[0] < width - 20 &&
          coords[1] > 20 &&
          coords[1] < height - 20
        ) {
          constGroup
            .append("text")
            .attr("x", coords[0])
            .attr("y", coords[1])
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", "#666")
            .attr("font-size", 9)
            .attr("font-style", "italic")
            .attr("opacity", 0.6)
            .text(name);
        }
      });
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

      const group = pointingGroup.append("g").attr("class", "pointing").attr("cursor", "pointer");

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
        .on("mouseenter", (event: MouseEvent) => {
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

    // Calculate legend height based on content
    let legendHeight = 10; // base padding
    if (colorScheme === "status") legendHeight += 45; // 3 status items
    if (showGalacticPlane) legendHeight += 18;
    if (showEcliptic) legendHeight += 18;
    legendHeight = Math.max(legendHeight, 30); // minimum height

    legend
      .append("rect")
      .attr("width", 110)
      .attr("height", legendHeight)
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

    // Add zoom and pan behavior
    // Note: Zoom transforms are applied directly to selectable elements

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 8])
      .on("zoom", (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        svg
          .selectAll("path, circle, text:not(.legend-text), line:not(.legend-line)")
          .attr("transform", event.transform.toString());
      });

    svg.call(zoom);

    // Add reset zoom on double-click
    svg.on("dblclick.zoom", () => {
      svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
    });
  }, [
    pointings,
    selectedProjection,
    width,
    height,
    showGalacticPlane,
    showEcliptic,
    showConstellations,
    constOptions,
    constellationNames,
    constellationLines,
    constellationBounds,
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
              onChange={(e) => setSelectedProjection(e.target.value as ProjectionType)}
              className="ml-2 px-2 py-1 border border-gray-300 rounded text-sm"
            >
              <option value="aitoff">Aitoff</option>
              <option value="mollweide">Mollweide</option>
              <option value="hammer">Hammer</option>
              <option value="mercator">Mercator</option>
            </select>
          </label>
        </div>

        <div className="text-sm text-gray-500">{pointings.length} pointings</div>
      </div>

      {/* SVG Map */}
      <div className="relative">
        <svg ref={svgRef} width={width} height={height} className="rounded-lg shadow-md" />

        {/* Constellation loading indicator */}
        {isLoadingConstellations && (
          <div className="absolute top-2 right-2 bg-gray-800/80 text-white text-xs px-2 py-1 rounded">
            Loading constellations...
          </div>
        )}

        {/* Constellation load error */}
        {constellationLoadError && (
          <div className="absolute top-2 right-2 bg-red-800/80 text-white text-xs px-2 py-1 rounded">
            {constellationLoadError}
          </div>
        )}
      </div>

      {/* Tooltip */}
      {hoveredPointing && (
        <div
          className="fixed bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 pointer-events-none"
          style={{
            left: tooltipPos.x + 15,
            top: tooltipPos.y + 15,
          }}
        >
          <p className="font-semibold text-sm">{hoveredPointing.label || hoveredPointing.id}</p>
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
