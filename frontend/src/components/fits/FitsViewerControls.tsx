import React, { useState } from "react";

export interface FitsViewerControlsProps {
  /** Current color map */
  colorMap: string;
  /** Current scale type */
  scale: string;
  /** Current contrast level (0-1) */
  contrast: number;
  /** Current bias level (0-1) */
  bias: number;
  /** Whether regions are visible */
  showRegions: boolean;
  /** Whether crosshair is visible */
  showCrosshair: boolean;
  /** Change handler */
  onChange: (values: Partial<FitsViewerControlsValues>) => void;
  /** Zoom in handler */
  onZoomIn?: () => void;
  /** Zoom out handler */
  onZoomOut?: () => void;
  /** Zoom to fit handler */
  onZoomFit?: () => void;
  /** Export handler */
  onExport?: (format: "png" | "fits") => void;
}

export interface FitsViewerControlsValues {
  colorMap: string;
  scale: string;
  contrast: number;
  bias: number;
  showRegions: boolean;
  showCrosshair: boolean;
}

const COLOR_MAPS = [
  "grey",
  "heat",
  "cool",
  "rainbow",
  "viridis",
  "plasma",
  "magma",
  "inferno",
  "cubehelix",
  "red",
  "green",
  "blue",
];

const SCALES = ["linear", "log", "sqrt", "squared", "asinh", "sinh", "histeq", "power"];

/**
 * Control panel for FITS viewer settings.
 */
const FitsViewerControls: React.FC<FitsViewerControlsProps> = ({
  colorMap,
  scale,
  contrast,
  bias,
  showRegions,
  showCrosshair,
  onChange,
  onZoomIn,
  onZoomOut,
  onZoomFit,
  onExport,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <span className="font-semibold text-sm text-gray-700">Display Settings</span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="p-3 space-y-4">
          {/* Zoom buttons */}
          <div className="flex gap-2">
            <button
              onClick={onZoomIn}
              className="flex-1 px-2 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded transition-colors"
              title="Zoom in"
            >
              <svg
                className="w-4 h-4 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
                />
              </svg>
            </button>
            <button
              onClick={onZoomOut}
              className="flex-1 px-2 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded transition-colors"
              title="Zoom out"
            >
              <svg
                className="w-4 h-4 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM7 10h6"
                />
              </svg>
            </button>
            <button
              onClick={onZoomFit}
              className="flex-1 px-2 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded transition-colors"
              title="Fit to window"
            >
              <svg
                className="w-4 h-4 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                />
              </svg>
            </button>
          </div>

          {/* Color map */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">Color Map</label>
            <select
              value={colorMap}
              onChange={(e) => onChange({ colorMap: e.target.value })}
              className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
            >
              {COLOR_MAPS.map((cm) => (
                <option key={cm} value={cm}>
                  {cm.charAt(0).toUpperCase() + cm.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Scale */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">Scale</label>
            <select
              value={scale}
              onChange={(e) => onChange({ scale: e.target.value })}
              className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
            >
              {SCALES.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Contrast slider */}
          <div>
            <label className="flex items-center justify-between text-sm text-gray-600 mb-1">
              <span>Contrast</span>
              <span className="text-gray-400">{(contrast * 100).toFixed(0)}%</span>
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={contrast}
              onChange={(e) => onChange({ contrast: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          {/* Bias slider */}
          <div>
            <label className="flex items-center justify-between text-sm text-gray-600 mb-1">
              <span>Bias</span>
              <span className="text-gray-400">{(bias * 100).toFixed(0)}%</span>
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={bias}
              onChange={(e) => onChange({ bias: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          {/* Toggle options */}
          <div className="space-y-2 pt-2 border-t border-gray-100">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showRegions}
                onChange={(e) => onChange({ showRegions: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <span className="text-sm">Show regions</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showCrosshair}
                onChange={(e) => onChange({ showCrosshair: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <span className="text-sm">Show crosshair</span>
            </label>
          </div>

          {/* Export buttons */}
          {onExport && (
            <div className="flex gap-2 pt-2 border-t border-gray-100">
              <button
                onClick={() => onExport("png")}
                className="flex-1 px-2 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary-dark transition-colors"
              >
                Export PNG
              </button>
              <button
                onClick={() => onExport("fits")}
                className="flex-1 px-2 py-1.5 text-sm border border-primary text-primary rounded hover:bg-primary/10 transition-colors"
              >
                Export FITS
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FitsViewerControls;
