import React, {
  useEffect,
  useRef,
  useState,
  useMemo,
  useCallback,
} from "react";
import * as d3 from "d3";
import { geoMollweide } from "d3-geo-projection";

// ============================================================================
// Types and Interfaces
// ============================================================================

export interface Pointing {
  id: string;
  ra: number; // degrees
  dec: number; // degrees
  radius?: number; // field of view radius in degrees
  label?: string;
  status?: "completed" | "scheduled" | "failed" | "queued";
  epoch?: string; // ISO date string
  qaGrade?: string;
}

interface SurveyRegion {
  id: string;
  name: string;
  color: string;
  decRange: [number, number];
  raRange: [number, number] | null;
  fillOpacity: number;
  showInLegend: boolean;
}

interface FilterState {
  status: Set<string>;
  dateRange: [Date | null, Date | null];
  qaGrade: Set<string>;
  surveys: Set<string>;
}

interface CoverageStats {
  totalArea: number;
  nvssOverlap: number;
  vlassOverlap: number;
  racsOverlap: number;
  firstOverlap: number;
  uniquePointings: number;
}

// ============================================================================
// Constants
// ============================================================================

const SURVEY_REGIONS: SurveyRegion[] = [
  {
    id: "nvss",
    name: "NVSS",
    color: "#ff99cc",
    decRange: [-40, 90],
    raRange: null,
    fillOpacity: 0.25,
    showInLegend: true,
  },
  {
    id: "vlass",
    name: "VLASS",
    color: "#66ccff",
    decRange: [-40, 90],
    raRange: null,
    fillOpacity: 0.15,
    showInLegend: true,
  },
  {
    id: "racs",
    name: "RACS",
    color: "#99ff99",
    decRange: [-90, 41],
    raRange: null,
    fillOpacity: 0.2,
    showInLegend: true,
  },
];

const FIRST_REGIONS = [
  {
    name: "FIRST NGC",
    polygon: [
      [110, -10],
      [110, 57],
      [265, 57],
      [265, -10],
      [110, -10],
    ] as [number, number][],
  },
  {
    name: "FIRST SGC",
    polygon: [
      [320, -10],
      [320, 2],
      [360, 2],
      [360, -10],
      [320, -10],
    ] as [number, number][],
  },
  {
    name: "FIRST SGC2",
    polygon: [
      [0, -10],
      [0, 2],
      [50, 2],
      [50, -10],
      [0, -10],
    ] as [number, number][],
  },
];

const FIRST_COLOR = "#cc66ff";
const FIRST_FILL_OPACITY = 0.2;
const DSA110_HORIZON_DEC = -53;

// Galactic plane coordinates (simplified equatorial representation)
// Real implementation would use proper coordinate transforms
const GALACTIC_PLANE_POINTS: [number, number][] = [];
for (let l = 0; l <= 360; l += 5) {
  // Approximate galactic to equatorial conversion
  const lRad = (l * Math.PI) / 180;
  const dec = 27.4 * Math.sin(lRad - 0.575) - 0.5;
  const ra = ((l + 192.25) % 360) - 180;
  GALACTIC_PLANE_POINTS.push([ra, dec]);
}

// ============================================================================
// Helper Functions
// ============================================================================

const getPointingColor = (status?: string): string => {
  switch (status) {
    case "completed":
      return "#10b981";
    case "failed":
      return "#ef4444";
    case "scheduled":
      return "#f59e0b";
    case "queued":
      return "#8b5cf6";
    default:
      return "#00cccc";
  }
};

const formatCoord = (ra: number, dec: number): string => {
  const raH = ra / 15;
  const h = Math.floor(raH);
  const m = Math.floor((raH - h) * 60);
  const raStr = `${h}h ${m.toString().padStart(2, "0")}m`;
  const sign = dec >= 0 ? "+" : "";
  const d = Math.floor(Math.abs(dec));
  const dm = Math.floor((Math.abs(dec) - d) * 60);
  const decStr = `${sign}${d}° ${dm.toString().padStart(2, "0")}'`;
  return `RA: ${raStr}, Dec: ${decStr}`;
};

const calculateCoverageStats = (
  pointings: Pointing[],
  defaultRadius: number
): CoverageStats => {
  const fovArea = Math.PI * defaultRadius * defaultRadius;
  const totalArea = pointings.length * fovArea;

  let nvssCount = 0,
    vlassCount = 0,
    racsCount = 0,
    firstCount = 0;

  pointings.forEach((p) => {
    if (p.dec >= -40 && p.dec <= 90) nvssCount++;
    if (p.dec >= -40 && p.dec <= 90) vlassCount++;
    if (p.dec >= -90 && p.dec <= 41) racsCount++;
    if (
      (p.ra >= 110 && p.ra <= 265 && p.dec >= -10 && p.dec <= 57) ||
      (p.ra >= 320 && p.dec >= -10 && p.dec <= 2) ||
      (p.ra <= 50 && p.dec >= -10 && p.dec <= 2)
    ) {
      firstCount++;
    }
  });

  const total = Math.max(pointings.length, 1);
  return {
    totalArea: Math.round(totalArea * 100) / 100,
    nvssOverlap: Math.round((nvssCount / total) * 100),
    vlassOverlap: Math.round((vlassCount / total) * 100),
    racsOverlap: Math.round((racsCount / total) * 100),
    firstOverlap: Math.round((firstCount / total) * 100),
    uniquePointings: pointings.length,
  };
};

// ============================================================================
// Sub-components
// ============================================================================

interface ControlPanelProps {
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  showGalacticPlane: boolean;
  onToggleGalacticPlane: () => void;
  surveys: Set<string>;
  onSurveyToggle: (surveyId: string) => void;
  isPlaying: boolean;
  onPlayToggle: () => void;
  playbackSpeed: number;
  onSpeedChange: (speed: number) => void;
  currentEpochIndex: number;
  totalEpochs: number;
  onEpochChange: (index: number) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onExport: (format: "png" | "svg" | "csv") => void;
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  filters,
  onFilterChange,
  showGalacticPlane,
  onToggleGalacticPlane,
  surveys,
  onSurveyToggle,
  isPlaying,
  onPlayToggle,
  playbackSpeed,
  onSpeedChange,
  currentEpochIndex,
  totalEpochs,
  onEpochChange,
  searchQuery,
  onSearchChange,
  onExport,
}) => {
  const statusOptions = ["completed", "scheduled", "failed", "queued"];

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3 space-y-3">
      {/* Row 1: Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-600">Status:</span>
          <div className="flex gap-1">
            {statusOptions.map((status) => (
              <button
                key={status}
                onClick={() => {
                  const newStatus = new Set(filters.status);
                  if (newStatus.has(status)) {
                    newStatus.delete(status);
                  } else {
                    newStatus.add(status);
                  }
                  onFilterChange({ ...filters, status: newStatus });
                }}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  filters.status.has(status)
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        {/* Survey Toggles */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-600">Surveys:</span>
          <div className="flex gap-1">
            {["nvss", "vlass", "racs", "first"].map((s) => (
              <button
                key={s}
                onClick={() => onSurveyToggle(s)}
                className={`px-2 py-1 text-xs rounded uppercase transition-colors ${
                  surveys.has(s)
                    ? "bg-purple-500 text-white"
                    : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Galactic Plane Toggle */}
        <button
          onClick={onToggleGalacticPlane}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            showGalacticPlane
              ? "bg-yellow-500 text-white"
              : "bg-gray-200 text-gray-600 hover:bg-gray-300"
          }`}
        >
          Galactic Plane
        </button>
      </div>

      {/* Row 2: Search and Timeline */}
      <div className="flex flex-wrap gap-4 items-center">
        {/* Search */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-600">Search:</span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="RA, Dec or source name..."
            className="px-2 py-1 text-xs border border-gray-300 rounded w-48 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Timeline Controls */}
        {totalEpochs > 1 && (
          <div className="flex items-center gap-2">
            <button
              onClick={onPlayToggle}
              className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              {isPlaying ? "Pause" : "Play"}
            </button>
            <input
              type="range"
              min={0}
              max={totalEpochs - 1}
              value={currentEpochIndex}
              onChange={(e) => onEpochChange(parseInt(e.target.value))}
              className="w-32"
            />
            <span className="text-xs text-gray-600">
              {currentEpochIndex + 1}/{totalEpochs}
            </span>
            <select
              value={playbackSpeed}
              onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
              className="text-xs border border-gray-300 rounded px-1"
            >
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={4}>4x</option>
            </select>
          </div>
        )}

        {/* Export Buttons */}
        <div className="flex items-center gap-1 ml-auto">
          <button
            onClick={() => onExport("png")}
            className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            title="Export as PNG"
          >
            PNG
          </button>
          <button
            onClick={() => onExport("svg")}
            className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            title="Export as SVG"
          >
            SVG
          </button>
          <button
            onClick={() => onExport("csv")}
            className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            title="Export pointings as CSV"
          >
            CSV
          </button>
        </div>
      </div>
    </div>
  );
};

interface StatsBarProps {
  stats: CoverageStats;
  filteredCount: number;
  totalCount: number;
}

const StatsBar: React.FC<StatsBarProps> = ({
  stats,
  filteredCount,
  totalCount,
}) => (
  <div className="bg-gray-800 text-white text-xs py-2 px-4 rounded-b-lg flex items-center justify-between">
    <div className="flex gap-4">
      <span>
        <strong>{filteredCount}</strong>/{totalCount} pointings
      </span>
      <span>
        <strong>{stats.totalArea.toFixed(1)}</strong> sq.deg
      </span>
    </div>
    <div className="flex gap-3">
      <span className="text-pink-300">NVSS: {stats.nvssOverlap}%</span>
      <span className="text-cyan-300">VLASS: {stats.vlassOverlap}%</span>
      <span className="text-green-300">RACS: {stats.racsOverlap}%</span>
      <span className="text-purple-300">FIRST: {stats.firstOverlap}%</span>
    </div>
  </div>
);

interface MiniMapProps {
  viewCenter: [number, number];
  zoomLevel: number;
  onNavigate: (ra: number, dec: number) => void;
}

const MiniMap: React.FC<MiniMapProps> = ({
  viewCenter,
  zoomLevel,
  onNavigate,
}) => {
  const miniRef = useRef<SVGSVGElement>(null);
  const size = 120;

  useEffect(() => {
    if (!miniRef.current || zoomLevel <= 1) return;

    const svg = d3.select(miniRef.current);
    svg.selectAll("*").remove();

    const proj = geoMollweide()
      .scale(size / 6)
      .translate([size / 2, size / 2]);

    const path = d3.geoPath(proj);
    const graticule = d3.geoGraticule().outline();

    // Background
    svg
      .append("rect")
      .attr("width", size)
      .attr("height", size)
      .attr("fill", "#1f2937")
      .attr("rx", 4);

    // Outline
    svg
      .append("path")
      .datum(graticule)
      .attr("d", path)
      .attr("fill", "#374151")
      .attr("stroke", "#6b7280")
      .attr("stroke-width", 1);

    // Viewport indicator
    const viewportWidth = 60 / zoomLevel;
    const viewportHeight = 40 / zoomLevel;
    let ra = viewCenter[0];
    if (ra > 180) ra -= 360;

    const centerCoords = proj([ra, viewCenter[1]]);
    if (centerCoords) {
      svg
        .append("rect")
        .attr("x", centerCoords[0] - viewportWidth / 2)
        .attr("y", centerCoords[1] - viewportHeight / 2)
        .attr("width", viewportWidth)
        .attr("height", viewportHeight)
        .attr("fill", "none")
        .attr("stroke", "#60a5fa")
        .attr("stroke-width", 2)
        .style("cursor", "move");
    }

    // Click handler
    svg.on("click", (event: MouseEvent) => {
      const [x, y] = d3.pointer(event);
      const coords = proj.invert?.([x, y]);
      if (coords) {
        let newRa = coords[0];
        if (newRa < 0) newRa += 360;
        onNavigate(newRa, coords[1]);
      }
    });
  }, [viewCenter, zoomLevel, onNavigate, size]);

  if (zoomLevel <= 1) return null;

  return (
    <div className="absolute bottom-12 right-4 bg-gray-900 rounded-lg shadow-lg p-1 z-20">
      <svg ref={miniRef} width={size} height={size} />
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export interface SkyCoverageMapVASTProps {
  pointings: Pointing[];
  width?: number;
  height?: number;
  defaultRadius?: number;
  onPointingClick?: (pointing: Pointing) => void;
  className?: string;
  totalImages?: number;
}

const SkyCoverageMapVAST: React.FC<SkyCoverageMapVASTProps> = ({
  pointings,
  width: propWidth,
  height: propHeight = 500,
  defaultRadius = 1.5,
  onPointingClick,
  className = "",
  totalImages,
}) => {
  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  // State
  const [containerWidth, setContainerWidth] = useState(propWidth || 800);
  const [hoveredPointing, setHoveredPointing] = useState<Pointing | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [highlightedId, setHighlightedId] = useState<string | null>(null);

  // Zoom/Pan state
  const [zoomLevel, setZoomLevel] = useState(1);
  const [viewCenter, setViewCenter] = useState<[number, number]>([180, 0]);

  // Filter state
  const [filters, setFilters] = useState<FilterState>({
    status: new Set(["completed", "scheduled", "failed", "queued"]),
    dateRange: [null, null],
    qaGrade: new Set(),
    surveys: new Set(["nvss", "vlass", "racs", "first"]),
  });

  // Display options
  const [showGalacticPlane, setShowGalacticPlane] = useState(false);
  const [visibleSurveys, setVisibleSurveys] = useState(
    new Set(["nvss", "vlass", "racs", "first"])
  );

  // Timeline/Animation state
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [currentEpochIndex, setCurrentEpochIndex] = useState(0);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");

  // Responsive sizing (Feature #8)
  useEffect(() => {
    if (propWidth) {
      setContainerWidth(propWidth);
      return;
    }

    const updateWidth = () => {
      if (containerRef.current) {
        const width = containerRef.current.getBoundingClientRect().width;
        setContainerWidth(Math.max(width, 400));
      }
    };

    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [propWidth]);

  // Get unique epochs for timeline (Feature #1)
  const epochs = useMemo(() => {
    const epochSet = new Set<string>();
    pointings.forEach((p) => {
      if (p.epoch) epochSet.add(p.epoch);
    });
    return Array.from(epochSet).sort();
  }, [pointings]);

  // Filter pointings (Feature #3)
  const filteredPointings = useMemo(() => {
    let result = pointings;

    // Status filter
    if (filters.status.size > 0 && filters.status.size < 4) {
      result = result.filter((p) => !p.status || filters.status.has(p.status));
    }

    // Epoch filter for timeline playback
    if (epochs.length > 1 && currentEpochIndex < epochs.length) {
      const currentEpoch = epochs[currentEpochIndex];
      result = result.filter((p) => !p.epoch || p.epoch <= currentEpoch);
    }

    // Search filter (Feature #5)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      const coordMatch = query.match(
        /^(\d+(?:\.\d+)?)\s*[h°]?\s*(\d+(?:\.\d+)?)?/
      );
      if (coordMatch) {
        const searchRa = parseFloat(coordMatch[1]);
        const searchDec = coordMatch[2] ? parseFloat(coordMatch[2]) : null;
        result = result.filter((p) => {
          const raDiff = Math.abs(p.ra - searchRa);
          if (searchDec !== null) {
            const decDiff = Math.abs(p.dec - searchDec);
            return raDiff < 5 && decDiff < 5;
          }
          return raDiff < 10;
        });
      } else {
        result = result.filter(
          (p) =>
            p.label?.toLowerCase().includes(query) ||
            p.id.toLowerCase().includes(query)
        );
      }
    }

    return result;
  }, [pointings, filters, epochs, currentEpochIndex, searchQuery]);

  // Update highlighted ID when search results change (moved from useMemo to avoid infinite loop)
  useEffect(() => {
    if (searchQuery.length >= 2 && filteredPointings.length > 0) {
      setHighlightedId(filteredPointings[0].id);
    } else if (searchQuery.length < 2) {
      setHighlightedId(null);
    }
  }, [filteredPointings, searchQuery]);

  // Calculate statistics (Feature #4)
  const stats = useMemo(
    () => calculateCoverageStats(filteredPointings, defaultRadius),
    [filteredPointings, defaultRadius]
  );

  // Timeline playback effect (Feature #1)
  useEffect(() => {
    if (!isPlaying || epochs.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentEpochIndex((prev) => {
        if (prev >= epochs.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 1000 / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, epochs.length, playbackSpeed]);

  // Calculate dimensions
  const width = containerWidth;
  const height = propHeight;
  const legendHeight = 32;
  const statsHeight = 32;
  const mapHeight = height - legendHeight - statsHeight;
  const margin = useMemo(
    () => ({ top: 10, right: 30, bottom: 30, left: 30 }),
    []
  );
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = mapHeight - margin.top - margin.bottom;

  // Missing data warning
  const hasImages = totalImages !== undefined && totalImages > 0;
  const missingCount = hasImages ? totalImages - pointings.length : 0;
  const missingPercentage = hasImages
    ? Math.round((missingCount / totalImages) * 100)
    : 0;
  const showMissingDataWarning = hasImages && missingPercentage > 50;

  // Export handlers (Feature #7)
  const handleExport = useCallback(
    (format: "png" | "svg" | "csv") => {
      if (format === "csv") {
        const csvContent = [
          "id,ra,dec,status,epoch,label",
          ...filteredPointings.map(
            (p) =>
              `${p.id},${p.ra},${p.dec},${p.status || ""},${p.epoch || ""},${
                p.label || ""
              }`
          ),
        ].join("\n");
        const blob = new Blob([csvContent], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `sky_coverage_${
          new Date().toISOString().split("T")[0]
        }.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else if (svgRef.current) {
        const svgData = new XMLSerializer().serializeToString(svgRef.current);

        if (format === "svg") {
          const blob = new Blob([svgData], { type: "image/svg+xml" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `sky_coverage_${
            new Date().toISOString().split("T")[0]
          }.svg`;
          a.click();
          URL.revokeObjectURL(url);
        } else {
          // PNG export
          const canvas = document.createElement("canvas");
          canvas.width = width * 2;
          canvas.height = (mapHeight + legendHeight) * 2;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            const img = new Image();
            img.onload = () => {
              ctx.fillStyle = "white";
              ctx.fillRect(0, 0, canvas.width, canvas.height);
              ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
              const url = canvas.toDataURL("image/png");
              const a = document.createElement("a");
              a.href = url;
              a.download = `sky_coverage_${
                new Date().toISOString().split("T")[0]
              }.png`;
              a.click();
            };
            img.src = "data:image/svg+xml;base64," + btoa(svgData);
          }
        }
      }
    },
    [filteredPointings, width, mapHeight, legendHeight]
  );

  // Navigation handler for mini-map (Feature #9)
  const handleNavigate = useCallback((ra: number, dec: number) => {
    setViewCenter([ra, dec]);
  }, []);

  // Main D3 rendering effect
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Create projection (Feature #2 - zoom support)
    // Use divisor of 7 to leave margin at top/bottom edges
    const proj = geoMollweide()
      .scale((innerWidth / 7) * zoomLevel)
      .translate([
        margin.left + innerWidth / 2,
        legendHeight + margin.top + innerHeight / 2,
      ])
      .rotate([180 - viewCenter[0], 0, 0]);

    const path = d3.geoPath(proj);

    // White background
    svg
      .append("rect")
      .attr("width", width)
      .attr("height", mapHeight + legendHeight)
      .attr("fill", "white");

    // Get projection bounds
    const graticuleOutline = d3.geoGraticule().outline();
    const outlineBounds = path.bounds(graticuleOutline);
    const mapX = outlineBounds[0][0];
    const mapY = outlineBounds[0][1];
    const mapW = outlineBounds[1][0] - outlineBounds[0][0];
    const mapH = outlineBounds[1][1] - outlineBounds[0][1];

    // Clip path
    const clipId = `vast-clip-${Math.random().toString(36).substr(2, 9)}`;
    svg
      .append("defs")
      .append("clipPath")
      .attr("id", clipId)
      .append("path")
      .datum(graticuleOutline)
      .attr("d", path);

    // GSM background
    svg
      .append("image")
      .attr("clip-path", `url(#${clipId})`)
      .attr("href", "/gsm_mollweide_gray.png")
      .attr("x", mapX)
      .attr("y", mapY)
      .attr("width", mapW)
      .attr("height", mapH)
      .attr("preserveAspectRatio", "none")
      .attr("opacity", 1);

    // DSA-110 visibility horizon
    const horizonRaSteps = 72;
    const horizonPolygon: [number, number][] = [];
    for (let i = 0; i <= horizonRaSteps; i++) {
      const ra = -180 + (360 * i) / horizonRaSteps;
      horizonPolygon.push([ra, DSA110_HORIZON_DEC]);
    }
    for (let i = horizonRaSteps; i >= 0; i--) {
      const ra = -180 + (360 * i) / horizonRaSteps;
      horizonPolygon.push([ra, -90]);
    }

    const horizonGeoPolygon: GeoJSON.Feature<GeoJSON.Polygon> = {
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [horizonPolygon] },
    };

    svg
      .append("path")
      .datum(horizonGeoPolygon)
      .attr("d", path)
      .attr("clip-path", `url(#${clipId})`)
      .attr("fill", "#dc2626")
      .attr("fill-opacity", 0.15)
      .attr("stroke", "#dc2626")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "8,4");

    // Galactic plane (Feature #6)
    if (showGalacticPlane) {
      const galacticLine: GeoJSON.Feature<GeoJSON.LineString> = {
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: GALACTIC_PLANE_POINTS },
      };

      svg
        .append("path")
        .datum(galacticLine)
        .attr("d", path)
        .attr("clip-path", `url(#${clipId})`)
        .attr("fill", "none")
        .attr("stroke", "#fbbf24")
        .attr("stroke-width", 3)
        .attr("stroke-opacity", 0.8);

      // Galactic center marker
      const gcCoords = proj([-93.5, -29]);
      if (gcCoords) {
        svg
          .append("text")
          .attr("x", gcCoords[0])
          .attr("y", gcCoords[1])
          .attr("fill", "#fbbf24")
          .attr("font-size", 16)
          .attr("text-anchor", "middle")
          .text("✦");
      }
    }

    // Graticule
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

    // RA labels
    const raLabels = [150, 120, 90, 60, 30, 0, 330, 300, 270, 240, 210];
    raLabels.forEach((ra) => {
      const coords = proj([ra - 180, 0]);
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

    // Dec labels
    const decLabels = [60, 30, 0, -30, -60];
    decLabels.forEach((dec) => {
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

    // Survey footprints (Feature #3 - toggleable)
    const surveysGroup = svg.append("g").attr("class", "surveys");

    SURVEY_REGIONS.forEach((survey) => {
      if (!visibleSurveys.has(survey.id)) return;

      const raSteps = 72;
      const topPoints: [number, number][] = [];
      const bottomPoints: [number, number][] = [];
      for (let i = 0; i <= raSteps; i++) {
        const ra = -180 + (360 * i) / raSteps;
        topPoints.push([ra, survey.decRange[1]]);
        bottomPoints.push([ra, survey.decRange[0]]);
      }
      const polygon = [...topPoints, ...bottomPoints.reverse()];

      const geoPolygon: GeoJSON.Feature<GeoJSON.Polygon> = {
        type: "Feature",
        properties: {},
        geometry: { type: "Polygon", coordinates: [polygon] },
      };

      surveysGroup
        .append("path")
        .datum(geoPolygon)
        .attr("d", path)
        .attr("clip-path", `url(#${clipId})`)
        .attr("fill", survey.color)
        .attr("fill-opacity", survey.fillOpacity)
        .attr("stroke", survey.color)
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "6,3");
    });

    // FIRST survey
    if (visibleSurveys.has("first")) {
      FIRST_REGIONS.forEach((region) => {
        const projectedPolygon = region.polygon.map(
          ([ra, dec]): [number, number] => [ra > 180 ? ra - 360 : ra, dec]
        );

        const geoPolygon: GeoJSON.Feature<GeoJSON.Polygon> = {
          type: "Feature",
          properties: {},
          geometry: { type: "Polygon", coordinates: [projectedPolygon] },
        };

        surveysGroup
          .append("path")
          .datum(geoPolygon)
          .attr("d", path)
          .attr("clip-path", `url(#${clipId})`)
          .attr("fill", FIRST_COLOR)
          .attr("fill-opacity", FIRST_FILL_OPACITY)
          .attr("stroke", FIRST_COLOR)
          .attr("stroke-width", 1.5)
          .attr("stroke-dasharray", "6,3");
      });
    }

    // Pointings (Feature #10 - queued observations)
    const pointingsGroup = svg.append("g").attr("class", "pointings");

    filteredPointings.forEach((pointing) => {
      let ra = pointing.ra;
      if (ra > 180) ra -= 360;

      const coords = proj([ra, pointing.dec]);
      if (!coords) return;

      const radius = pointing.radius ?? defaultRadius;
      const refPoint = proj([ra + radius, pointing.dec]);
      let pixelRadius = 5;
      if (refPoint) {
        pixelRadius = Math.max(Math.abs(refPoint[0] - coords[0]), 5);
      }

      const isQueued = pointing.status === "queued";
      const isHighlighted = pointing.id === highlightedId;
      const color = getPointingColor(pointing.status);

      const group = pointingsGroup
        .append("g")
        .attr("class", "pointing")
        .style("cursor", "pointer");

      // Circle (different style for queued observations - Feature #10)
      const circle = group
        .append("circle")
        .attr("cx", coords[0])
        .attr("cy", coords[1])
        .attr("r", isHighlighted ? pixelRadius * 1.5 : pixelRadius)
        .attr("fill", isQueued ? "none" : color)
        .attr("fill-opacity", isQueued ? 0 : 0.4)
        .attr("stroke", color)
        .attr("stroke-width", isHighlighted ? 4 : isQueued ? 1.5 : 2)
        .attr("stroke-dasharray", isQueued ? "4,2" : "none");

      // Highlight ring for searched pointing (Feature #5)
      if (isHighlighted) {
        group
          .append("circle")
          .attr("cx", coords[0])
          .attr("cy", coords[1])
          .attr("r", pixelRadius * 2)
          .attr("fill", "none")
          .attr("stroke", "#3b82f6")
          .attr("stroke-width", 2)
          .attr("stroke-dasharray", "4,2")
          .style("animation", "pulse 1s infinite");
      }

      // Event handlers
      group
        .on("mouseenter", (event: MouseEvent) => {
          setHoveredPointing(pointing);
          setTooltipPos({ x: event.clientX, y: event.clientY });
          circle.attr("fill-opacity", 0.7).attr("stroke-width", 3);
        })
        .on("mouseleave", () => {
          setHoveredPointing(null);
          circle
            .attr("fill-opacity", isQueued ? 0 : 0.4)
            .attr("stroke-width", isQueued ? 1.5 : 2);
        })
        .on("click", () => onPointingClick?.(pointing));
    });

    // Legend
    const legend = svg.append("g").attr("class", "legend");
    legend
      .append("rect")
      .attr("x", 0)
      .attr("y", 0)
      .attr("width", width)
      .attr("height", legendHeight)
      .attr("fill", "#f5f5f5")
      .attr("stroke", "#ddd");

    let xOffset = 15;

    // Status counts
    const statusCounts = {
      completed: filteredPointings.filter((p) => p.status === "completed")
        .length,
      failed: filteredPointings.filter((p) => p.status === "failed").length,
      scheduled: filteredPointings.filter((p) => p.status === "scheduled")
        .length,
      queued: filteredPointings.filter((p) => p.status === "queued").length,
    };

    Object.entries(statusCounts).forEach(([status, count]) => {
      if (count === 0) return;
      const color = getPointingColor(status);
      const isQueued = status === "queued";

      legend
        .append("circle")
        .attr("cx", xOffset + 6)
        .attr("cy", legendHeight / 2)
        .attr("r", 5)
        .attr("fill", isQueued ? "none" : color)
        .attr("fill-opacity", 0.5)
        .attr("stroke", color)
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", isQueued ? "2,1" : "none");

      legend
        .append("text")
        .attr("x", xOffset + 16)
        .attr("y", legendHeight / 2 + 4)
        .attr("fill", "#333")
        .attr("font-size", 10)
        .text(`${status} (${count})`);

      xOffset += 90;
    });

    xOffset += 20;

    // Survey legend items
    SURVEY_REGIONS.filter((s) => visibleSurveys.has(s.id)).forEach((survey) => {
      legend
        .append("rect")
        .attr("x", xOffset)
        .attr("y", legendHeight / 2 - 5)
        .attr("width", 14)
        .attr("height", 10)
        .attr("fill", survey.color)
        .attr("fill-opacity", 0.3)
        .attr("stroke", survey.color)
        .attr("stroke-dasharray", "3,2");

      legend
        .append("text")
        .attr("x", xOffset + 18)
        .attr("y", legendHeight / 2 + 4)
        .attr("fill", "#333")
        .attr("font-size", 10)
        .text(survey.name);

      xOffset += 60;
    });

    if (visibleSurveys.has("first")) {
      legend
        .append("rect")
        .attr("x", xOffset)
        .attr("y", legendHeight / 2 - 5)
        .attr("width", 14)
        .attr("height", 10)
        .attr("fill", FIRST_COLOR)
        .attr("fill-opacity", 0.3)
        .attr("stroke", FIRST_COLOR)
        .attr("stroke-dasharray", "3,2");

      legend
        .append("text")
        .attr("x", xOffset + 18)
        .attr("y", legendHeight / 2 + 4)
        .attr("fill", "#333")
        .attr("font-size", 10)
        .text("FIRST");

      xOffset += 55;
    }

    // Galactic plane legend (Feature #6)
    if (showGalacticPlane) {
      legend
        .append("line")
        .attr("x1", xOffset)
        .attr("y1", legendHeight / 2)
        .attr("x2", xOffset + 18)
        .attr("y2", legendHeight / 2)
        .attr("stroke", "#fbbf24")
        .attr("stroke-width", 3);

      legend
        .append("text")
        .attr("x", xOffset + 24)
        .attr("y", legendHeight / 2 + 4)
        .attr("fill", "#333")
        .attr("font-size", 10)
        .text("Galactic");

      xOffset += 70;
    }

    // Horizon legend
    legend
      .append("line")
      .attr("x1", xOffset)
      .attr("y1", legendHeight / 2)
      .attr("x2", xOffset + 18)
      .attr("y2", legendHeight / 2)
      .attr("stroke", "#dc2626")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "4,2");

    legend
      .append("text")
      .attr("x", xOffset + 24)
      .attr("y", legendHeight / 2 + 4)
      .attr("fill", "#333")
      .attr("font-size", 10)
      .text("Dec -53°");

    // Add zoom behavior (Feature #2)
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 8])
      .on("zoom", (event) => {
        setZoomLevel(event.transform.k);
      });

    svg.call(zoom);
    zoomRef.current = zoom;
  }, [
    filteredPointings,
    width,
    mapHeight,
    innerWidth,
    innerHeight,
    margin,
    legendHeight,
    defaultRadius,
    onPointingClick,
    showGalacticPlane,
    visibleSurveys,
    zoomLevel,
    viewCenter,
    highlightedId,
  ]);

  // Zoom controls (Feature #2)
  const handleZoomIn = () => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 1.5);
    }
  };

  const handleZoomOut = () => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 0.67);
    }
  };

  const handleResetZoom = () => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.transform, d3.zoomIdentity);
      setViewCenter([180, 0]);
    }
  };

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      {/* Control Panel */}
      <ControlPanel
        filters={filters}
        onFilterChange={setFilters}
        showGalacticPlane={showGalacticPlane}
        onToggleGalacticPlane={() => setShowGalacticPlane(!showGalacticPlane)}
        surveys={visibleSurveys}
        onSurveyToggle={(s) => {
          const newSurveys = new Set(visibleSurveys);
          if (newSurveys.has(s)) {
            newSurveys.delete(s);
          } else {
            newSurveys.add(s);
          }
          setVisibleSurveys(newSurveys);
        }}
        isPlaying={isPlaying}
        onPlayToggle={() => setIsPlaying(!isPlaying)}
        playbackSpeed={playbackSpeed}
        onSpeedChange={setPlaybackSpeed}
        currentEpochIndex={currentEpochIndex}
        totalEpochs={epochs.length}
        onEpochChange={setCurrentEpochIndex}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onExport={handleExport}
      />

      {/* Main Map Container */}
      <div className="relative">
        {/* Missing data warning - bottom left */}
        {showMissingDataWarning && (
          <div className="absolute bottom-2 left-2 z-10 bg-amber-100 border border-amber-300 text-amber-800 px-3 py-1.5 rounded-lg shadow-md flex items-center gap-2 text-xs">
            <span className="text-amber-500 font-bold">!</span>
            <span>
              <strong>{missingPercentage}%</strong> of images ({missingCount} of{" "}
              {totalImages}) missing coordinate data
            </span>
          </div>
        )}

        {/* Zoom Controls (Feature #2) */}
        <div className="absolute top-2 left-2 z-10 flex flex-col gap-1">
          <button
            onClick={handleZoomIn}
            className="w-8 h-8 bg-white border border-gray-300 rounded shadow text-lg hover:bg-gray-100"
            title="Zoom in"
          >
            +
          </button>
          <button
            onClick={handleZoomOut}
            className="w-8 h-8 bg-white border border-gray-300 rounded shadow text-lg hover:bg-gray-100"
            title="Zoom out"
          >
            −
          </button>
          <button
            onClick={handleResetZoom}
            className="w-8 h-8 bg-white border border-gray-300 rounded shadow text-xs hover:bg-gray-100"
            title="Reset view"
          >
            Reset
          </button>
        </div>

        {/* SVG Map */}
        <svg
          ref={svgRef}
          width={width}
          height={mapHeight + legendHeight}
          className="rounded-t shadow-sm"
          style={{ background: "white", cursor: "grab" }}
        />

        {/* Mini-map Navigator (Feature #9) */}
        <MiniMap
          viewCenter={viewCenter}
          zoomLevel={zoomLevel}
          onNavigate={handleNavigate}
        />

        {/* Stats Bar (Feature #4) */}
        <StatsBar
          stats={stats}
          filteredCount={filteredPointings.length}
          totalCount={pointings.length}
        />
      </div>

      {/* Tooltip */}
      {hoveredPointing && (
        <div
          className="fixed bg-white border border-gray-300 rounded-lg shadow-lg p-3 z-50 pointer-events-none text-sm max-w-xs"
          style={{ left: tooltipPos.x + 12, top: tooltipPos.y + 12 }}
        >
          <p className="font-semibold text-gray-900">
            {hoveredPointing.label || hoveredPointing.id}
          </p>
          <p className="text-gray-600 text-xs mt-1">
            {formatCoord(hoveredPointing.ra, hoveredPointing.dec)}
          </p>
          {hoveredPointing.status && (
            <p className="mt-1">
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                  hoveredPointing.status === "completed"
                    ? "bg-green-100 text-green-800"
                    : hoveredPointing.status === "failed"
                    ? "bg-red-100 text-red-800"
                    : hoveredPointing.status === "queued"
                    ? "bg-purple-100 text-purple-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {hoveredPointing.status}
              </span>
            </p>
          )}
          {hoveredPointing.epoch && (
            <p className="text-gray-500 text-xs mt-1">
              Epoch: {new Date(hoveredPointing.epoch).toLocaleDateString()}
            </p>
          )}
          {hoveredPointing.qaGrade && (
            <p className="text-gray-500 text-xs mt-1">
              QA: {hoveredPointing.qaGrade}
            </p>
          )}
          <p className="text-gray-400 text-xs mt-2 italic">
            Click to view details
          </p>
        </div>
      )}

      {/* CSS for animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

export default SkyCoverageMapVAST;
