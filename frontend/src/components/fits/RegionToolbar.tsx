import React, { useState, useCallback } from "react";
import type { JS9Region } from "../../types/js9.d";
import { logger } from "../../utils/logger";

/**
 * Region shape types that can be created.
 */
export type RegionShape = "circle" | "box" | "ellipse" | "polygon" | "point";

/**
 * Region format for export.
 */
export type RegionFormat = "ds9" | "crtf" | "json";

/**
 * Region created or exported from the toolbar.
 */
export interface Region {
  id: string;
  shape: RegionShape;
  x: number;
  y: number;
  radius?: number;
  width?: number;
  height?: number;
  points?: Array<{ x: number; y: number }>;
  text?: string;
  color?: string;
}

/**
 * Props for the RegionToolbar component.
 */
interface RegionToolbarProps {
  /** The JS9 display ID to operate on */
  displayId: string;
  /** Callback when regions are saved */
  onSave?: (regions: Region[], format: RegionFormat) => void;
  /** Callback when regions change */
  onChange?: (regions: Region[]) => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether toolbar is in compact mode */
  compact?: boolean;
}

/**
 * Default region colors for different shapes.
 */
const REGION_COLORS: Record<RegionShape, string> = {
  circle: "#22C55E", // green
  box: "#3B82F6", // blue
  ellipse: "#8B5CF6", // purple
  polygon: "#F59E0B", // amber
  point: "#EF4444", // red
};

/**
 * Region toolbar component for creating and managing JS9 regions.
 *
 * Provides tools for drawing circles, boxes, ellipses, polygons, and points.
 * Supports export in DS9, CRTF, and JSON formats.
 */
const RegionToolbar: React.FC<RegionToolbarProps> = ({
  displayId,
  onSave,
  onChange,
  className = "",
  compact = false,
}) => {
  const [activeShape, setActiveShape] = useState<RegionShape | null>(null);
  const [exportFormat, setExportFormat] = useState<RegionFormat>("ds9");

  /**
   * Get all current regions from JS9.
   */
  const getRegions = useCallback((): Region[] => {
    if (!window.JS9) return [];

    try {
      const js9Regions =
        window.JS9.GetRegions("all", { display: displayId }) || [];
      return js9Regions.map((r: JS9Region) => ({
        id: r.id,
        shape: r.shape as RegionShape,
        x: r.x,
        y: r.y,
        radius: r.radius,
        width: r.width,
        height: r.height,
        text: r.text,
        color: r.color,
      }));
    } catch (err) {
      logger.warn("Failed to get regions from JS9", { error: err });
      return [];
    }
  }, [displayId]);

  /**
   * Start drawing a region of the specified shape.
   */
  const startDrawing = useCallback(
    (shape: RegionShape) => {
      if (!window.JS9) {
        logger.error("JS9 not available");
        return;
      }

      try {
        // Add a new region of the specified shape
        window.JS9.AddRegions(
          shape,
          { color: REGION_COLORS[shape] },
          { display: displayId }
        );
        setActiveShape(shape);
        logger.debug(`Started drawing ${shape} region`);
      } catch (err) {
        logger.error("Failed to start region drawing", { error: err, shape });
      }
    },
    [displayId]
  );

  /**
   * Clear all regions.
   */
  const clearAllRegions = useCallback(() => {
    if (!window.JS9) return;

    try {
      window.JS9.RemoveRegions("all", { display: displayId });
      setActiveShape(null);
      onChange?.([]);
      logger.debug("Cleared all regions");
    } catch (err) {
      logger.error("Failed to clear regions", { error: err });
    }
  }, [displayId, onChange]);

  /**
   * Convert regions to DS9 format string.
   */
  const toDS9Format = useCallback((regions: Region[]): string => {
    const lines = [
      "# Region file format: DS9 version 4.1",
      "global color=green dashlist=8 3 width=1",
    ];

    for (const region of regions) {
      let line = "";
      const color = region.color || REGION_COLORS[region.shape];

      switch (region.shape) {
        case "circle":
          line = `circle(${region.x},${region.y},${
            region.radius || 10
          }) # color=${color}`;
          break;
        case "box":
          line = `box(${region.x},${region.y},${region.width || 20},${
            region.height || 20
          },0) # color=${color}`;
          break;
        case "ellipse":
          line = `ellipse(${region.x},${region.y},${region.width || 20},${
            region.height || 10
          },0) # color=${color}`;
          break;
        case "polygon":
          if (region.points && region.points.length > 0) {
            const coords = region.points.map((p) => `${p.x},${p.y}`).join(",");
            line = `polygon(${coords}) # color=${color}`;
          }
          break;
        case "point":
          line = `point(${region.x},${region.y}) # color=${color}`;
          break;
      }

      if (line) {
        if (region.text) {
          line += ` text={${region.text}}`;
        }
        lines.push(line);
      }
    }

    return lines.join("\n");
  }, []);

  /**
   * Convert regions to CRTF (CASA Region Text Format) string.
   */
  const toCRTFFormat = useCallback((regions: Region[]): string => {
    const lines = ["#CRTFv0 CASA Region Text Format version 0"];

    for (const region of regions) {
      let line = "";

      switch (region.shape) {
        case "circle":
          line = `circle [[${region.x}pix, ${region.y}pix], ${
            region.radius || 10
          }pix]`;
          break;
        case "box": {
          const hw = (region.width || 20) / 2;
          const hh = (region.height || 20) / 2;
          line = `box [[${region.x - hw}pix, ${region.y - hh}pix], [${
            region.x + hw
          }pix, ${region.y + hh}pix]]`;
          break;
        }
        case "ellipse":
          line = `ellipse [[${region.x}pix, ${region.y}pix], [${
            region.width || 20
          }pix, ${region.height || 10}pix], 0.0deg]`;
          break;
        case "polygon":
          if (region.points && region.points.length > 0) {
            const coords = region.points
              .map((p) => `[${p.x}pix, ${p.y}pix]`)
              .join(", ");
            line = `poly [${coords}]`;
          }
          break;
        case "point":
          line = `symbol [[${region.x}pix, ${region.y}pix], .]`;
          break;
      }

      if (line) {
        lines.push(line);
      }
    }

    return lines.join("\n");
  }, []);

  /**
   * Export regions in the selected format.
   */
  const exportRegions = useCallback(() => {
    const regions = getRegions();

    if (regions.length === 0) {
      logger.warn("No regions to export");
      return;
    }

    let content: string;
    let filename: string;
    let mimeType: string;

    switch (exportFormat) {
      case "ds9":
        content = toDS9Format(regions);
        filename = "regions.reg";
        mimeType = "text/plain";
        break;
      case "crtf":
        content = toCRTFFormat(regions);
        filename = "regions.crtf";
        mimeType = "text/plain";
        break;
      case "json":
      default:
        content = JSON.stringify(regions, null, 2);
        filename = "regions.json";
        mimeType = "application/json";
        break;
    }

    // Create and trigger download
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    logger.info(`Exported ${regions.length} regions as ${exportFormat}`);
  }, [exportFormat, getRegions, toDS9Format, toCRTFFormat]);

  /**
   * Save regions and call the onSave callback.
   */
  const handleSave = useCallback(() => {
    const regions = getRegions();
    onSave?.(regions, exportFormat);
    logger.info(`Saved ${regions.length} regions`);
  }, [getRegions, exportFormat, onSave]);

  // Compact button class
  const btnClass = compact
    ? "p-1.5 text-xs rounded hover:bg-gray-200 transition-colors"
    : "px-2 py-1 text-sm rounded hover:bg-gray-200 transition-colors";

  const activeBtnClass = "bg-blue-100 text-blue-700 hover:bg-blue-200";

  return (
    <div className={`region-toolbar bg-gray-100 rounded-lg p-2 ${className}`}>
      <div
        className={`flex ${compact ? "gap-1" : "gap-2"} flex-wrap items-center`}
      >
        {/* Shape buttons */}
        <div className="flex gap-1 border-r border-gray-300 pr-2">
          <button
            type="button"
            onClick={() => startDrawing("circle")}
            className={`${btnClass} ${
              activeShape === "circle" ? activeBtnClass : ""
            }`}
            title="Draw Circle"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="12" r="9" strokeWidth="2" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => startDrawing("box")}
            className={`${btnClass} ${
              activeShape === "box" ? activeBtnClass : ""
            }`}
            title="Draw Box"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <rect x="4" y="4" width="16" height="16" strokeWidth="2" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => startDrawing("ellipse")}
            className={`${btnClass} ${
              activeShape === "ellipse" ? activeBtnClass : ""
            }`}
            title="Draw Ellipse"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <ellipse cx="12" cy="12" rx="10" ry="6" strokeWidth="2" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => startDrawing("polygon")}
            className={`${btnClass} ${
              activeShape === "polygon" ? activeBtnClass : ""
            }`}
            title="Draw Polygon"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <polygon points="12,2 22,20 2,20" strokeWidth="2" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => startDrawing("point")}
            className={`${btnClass} ${
              activeShape === "point" ? activeBtnClass : ""
            }`}
            title="Add Point"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
        </div>

        {/* Clear button */}
        <button
          type="button"
          onClick={clearAllRegions}
          className={`${btnClass} text-red-600 hover:bg-red-100`}
          title="Clear All Regions"
        >
          {compact ? "×" : "Clear All"}
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Export format selector */}
        <select
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value as RegionFormat)}
          className="text-xs bg-white border border-gray-300 rounded px-1 py-0.5"
        >
          <option value="ds9">DS9</option>
          <option value="crtf">CRTF</option>
          <option value="json">JSON</option>
        </select>

        {/* Export/Save buttons */}
        <button
          type="button"
          onClick={exportRegions}
          className={`${btnClass} bg-gray-200 hover:bg-gray-300`}
          title="Export regions to file"
        >
          {compact ? "↓" : "Export"}
        </button>
        {onSave && (
          <button
            type="button"
            onClick={handleSave}
            className={`${btnClass} bg-blue-600 text-white hover:bg-blue-700`}
            title="Save regions"
          >
            {compact ? "✓" : "Save"}
          </button>
        )}
      </div>
    </div>
  );
};

export default RegionToolbar;
