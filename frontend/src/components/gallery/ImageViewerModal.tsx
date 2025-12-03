/**
 * Image Viewer Modal Component
 *
 * Full-screen modal for viewing FITS images with:
 * - Zoom and pan controls
 * - Colormap selection
 * - Brightness/contrast adjustment
 * - Coordinate grid overlay
 * - Keyboard navigation
 */

import React, { useState, useCallback, useEffect } from "react";
import FitsViewer from "../fits/FitsViewer";
import { config } from "../../config";

// ============================================================================
// Types
// ============================================================================

export type ColorMap =
  | "grey"
  | "heat"
  | "cool"
  | "rainbow"
  | "viridis"
  | "plasma"
  | "magma"
  | "inferno"
  | "cubehelix";

export type ScaleType =
  | "linear"
  | "log"
  | "sqrt"
  | "squared"
  | "asinh"
  | "sinh"
  | "histeq"
  | "power";

export interface ImageViewerSettings {
  colorMap: ColorMap;
  scale: ScaleType;
  contrast: number;
  bias: number;
  showGrid: boolean;
  showCrosshair: boolean;
  zoom: number;
}

export interface ImageViewerModalProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Image ID to display */
  imageId: string;
  /** Image path/name for display */
  imagePath?: string;
  /** Initial settings */
  initialSettings?: Partial<ImageViewerSettings>;
  /** Callback when coordinates are clicked */
  onCoordinateClick?: (ra: number, dec: number) => void;
  /** Enable navigation between images */
  onPrevious?: () => void;
  onNext?: () => void;
  hasPrevious?: boolean;
  hasNext?: boolean;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_SETTINGS: ImageViewerSettings = {
  colorMap: "grey",
  scale: "log",
  contrast: 0.5,
  bias: 0.5,
  showGrid: false,
  showCrosshair: false,
  zoom: 1,
};

const COLOR_MAPS: { value: ColorMap; label: string }[] = [
  { value: "grey", label: "Grayscale" },
  { value: "heat", label: "Heat" },
  { value: "cool", label: "Cool" },
  { value: "rainbow", label: "Rainbow" },
  { value: "viridis", label: "Viridis" },
  { value: "plasma", label: "Plasma" },
  { value: "magma", label: "Magma" },
  { value: "inferno", label: "Inferno" },
  { value: "cubehelix", label: "Cubehelix" },
];

const SCALE_TYPES: { value: ScaleType; label: string }[] = [
  { value: "linear", label: "Linear" },
  { value: "log", label: "Logarithmic" },
  { value: "sqrt", label: "Square Root" },
  { value: "squared", label: "Squared" },
  { value: "asinh", label: "Asinh" },
  { value: "sinh", label: "Sinh" },
  { value: "histeq", label: "Histogram Eq." },
  { value: "power", label: "Power" },
];

// ============================================================================
// Settings Panel Component
// ============================================================================

interface SettingsPanelProps {
  settings: ImageViewerSettings;
  onChange: (settings: Partial<ImageViewerSettings>) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomFit: () => void;
  onZoomActual: () => void;
  onExportPNG: () => void;
  onExportFITS: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  onChange,
  onZoomIn,
  onZoomOut,
  onZoomFit,
  onZoomActual,
  onExportPNG,
  onExportFITS,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="bg-gray-900/95 backdrop-blur text-white rounded-lg shadow-xl overflow-hidden w-72">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/50 transition-colors"
      >
        <span className="font-medium text-sm">Display Settings</span>
        <svg
          className={`w-4 h-4 transition-transform ${
            isExpanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Zoom controls */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">
              Zoom: {(settings.zoom * 100).toFixed(0)}%
            </label>
            <div className="flex gap-1">
              <button
                onClick={onZoomOut}
                className="flex-1 px-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-sm transition-colors"
                title="Zoom out"
              >
                −
              </button>
              <button
                onClick={onZoomFit}
                className="flex-1 px-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-sm transition-colors"
                title="Fit to view"
              >
                Fit
              </button>
              <button
                onClick={onZoomActual}
                className="flex-1 px-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-sm transition-colors"
                title="Actual size"
              >
                1:1
              </button>
              <button
                onClick={onZoomIn}
                className="flex-1 px-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-sm transition-colors"
                title="Zoom in"
              >
                +
              </button>
            </div>
          </div>

          {/* Color map */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Color Map
            </label>
            <select
              value={settings.colorMap}
              onChange={(e) =>
                onChange({ colorMap: e.target.value as ColorMap })
              }
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {COLOR_MAPS.map((cm) => (
                <option key={cm.value} value={cm.value}>
                  {cm.label}
                </option>
              ))}
            </select>
          </div>

          {/* Scale */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Scale</label>
            <select
              value={settings.scale}
              onChange={(e) => onChange({ scale: e.target.value as ScaleType })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {SCALE_TYPES.map((st) => (
                <option key={st.value} value={st.value}>
                  {st.label}
                </option>
              ))}
            </select>
          </div>

          {/* Contrast */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Contrast: {(settings.contrast * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={settings.contrast}
              onChange={(e) =>
                onChange({ contrast: parseFloat(e.target.value) })
              }
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* Bias (Brightness) */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Brightness: {(settings.bias * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={settings.bias}
              onChange={(e) => onChange({ bias: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* Overlays */}
          <div className="space-y-2">
            <label className="block text-xs text-gray-400">Overlays</label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.showGrid}
                onChange={(e) => onChange({ showGrid: e.target.checked })}
                className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <span className="text-sm">Coordinate Grid</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.showCrosshair}
                onChange={(e) => onChange({ showCrosshair: e.target.checked })}
                className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <span className="text-sm">Crosshair</span>
            </label>
          </div>

          {/* Export buttons */}
          <div className="pt-2 border-t border-gray-700">
            <label className="block text-xs text-gray-400 mb-2">Export</label>
            <div className="flex gap-2">
              <button
                onClick={onExportPNG}
                className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
              >
                PNG
              </button>
              <button
                onClick={onExportFITS}
                className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium transition-colors"
              >
                FITS
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Coordinate Display Component
// ============================================================================

interface CoordinateDisplayProps {
  ra?: string;
  dec?: string;
  pixelX?: number;
  pixelY?: number;
  value?: number;
}

const CoordinateDisplay: React.FC<CoordinateDisplayProps> = ({
  ra,
  dec,
  pixelX,
  pixelY,
  value,
}) => {
  if (!ra && !dec && pixelX === undefined && pixelY === undefined) {
    return null;
  }

  return (
    <div className="absolute bottom-4 left-4 bg-gray-900/90 backdrop-blur text-white px-4 py-2 rounded-lg text-sm font-mono">
      <div className="flex gap-6">
        {ra && dec && (
          <div className="space-x-2">
            <span className="text-gray-400">RA:</span>
            <span>{ra}</span>
            <span className="text-gray-400 ml-2">Dec:</span>
            <span>{dec}</span>
          </div>
        )}
        {pixelX !== undefined && pixelY !== undefined && (
          <div className="space-x-2">
            <span className="text-gray-400">X:</span>
            <span>{pixelX}</span>
            <span className="text-gray-400 ml-2">Y:</span>
            <span>{pixelY}</span>
          </div>
        )}
        {value !== undefined && (
          <div className="space-x-2">
            <span className="text-gray-400">Value:</span>
            <span>{value.toExponential(3)}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const ImageViewerModal: React.FC<ImageViewerModalProps> = ({
  isOpen,
  onClose,
  imageId,
  imagePath,
  initialSettings = {},
  onCoordinateClick,
  onPrevious,
  onNext,
  hasPrevious = false,
  hasNext = false,
}) => {
  // Settings state
  const [settings, setSettings] = useState<ImageViewerSettings>({
    ...DEFAULT_SETTINGS,
    ...initialSettings,
  });

  // Cursor coordinates
  const [cursorCoords, setCursorCoords] = useState<{
    ra?: string;
    dec?: string;
    pixelX?: number;
    pixelY?: number;
    value?: number;
  }>({});

  // FITS URL
  const fitsUrl = `${config.api.baseUrl}/images/${encodeURIComponent(
    imageId
  )}/fits`;
  const filename = imagePath?.split("/").pop() || imageId;

  // Settings change handler
  const handleSettingsChange = useCallback(
    (partial: Partial<ImageViewerSettings>) => {
      setSettings((prev) => ({ ...prev, ...partial }));
    },
    []
  );

  // Zoom handlers
  const handleZoomIn = useCallback(() => {
    setSettings((prev) => ({ ...prev, zoom: Math.min(prev.zoom * 1.5, 10) }));
  }, []);

  const handleZoomOut = useCallback(() => {
    setSettings((prev) => ({ ...prev, zoom: Math.max(prev.zoom / 1.5, 0.1) }));
  }, []);

  const handleZoomFit = useCallback(() => {
    setSettings((prev) => ({ ...prev, zoom: 1 }));
  }, []);

  const handleZoomActual = useCallback(() => {
    setSettings((prev) => ({ ...prev, zoom: 1 }));
  }, []);

  // Export handlers
  const handleExportPNG = useCallback(() => {
    const pngUrl = `${config.api.baseUrl}/images/${encodeURIComponent(
      imageId
    )}/png`;
    window.open(pngUrl, "_blank", "noopener,noreferrer");
  }, [imageId]);

  const handleExportFITS = useCallback(() => {
    window.open(fitsUrl, "_blank", "noopener,noreferrer");
  }, [fitsUrl]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          onClose();
          break;
        case "ArrowLeft":
          if (hasPrevious && onPrevious) {
            e.preventDefault();
            onPrevious();
          }
          break;
        case "ArrowRight":
          if (hasNext && onNext) {
            e.preventDefault();
            onNext();
          }
          break;
        case "+":
        case "=":
          handleZoomIn();
          break;
        case "-":
          handleZoomOut();
          break;
        case "0":
          handleZoomFit();
          break;
        case "g":
          setSettings((prev) => ({ ...prev, showGrid: !prev.showGrid }));
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    isOpen,
    onClose,
    hasPrevious,
    hasNext,
    onPrevious,
    onNext,
    handleZoomIn,
    handleZoomOut,
    handleZoomFit,
  ]);

  // Don't render if not open
  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-labelledby="image-viewer-title"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-900/95 backdrop-blur border-b border-gray-800">
        <div className="flex items-center gap-4">
          {/* Navigation buttons */}
          <div className="flex gap-1">
            <button
              onClick={onPrevious}
              disabled={!hasPrevious}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Previous image (←)"
            >
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <button
              onClick={onNext}
              disabled={!hasNext}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Next image (→)"
            >
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>

          {/* Title */}
          <h2 className="text-lg font-medium text-white">{filename}</h2>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
          title="Close (Esc)"
        >
          <svg
            className="w-5 h-5 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 relative overflow-hidden">
        {/* FITS Viewer */}
        <div className="absolute inset-0">
          <FitsViewer
            fitsUrl={fitsUrl}
            displayId="modal-viewer"
            width={window.innerWidth}
            height={window.innerHeight - 64}
            showControls={false}
            onCoordinateClick={onCoordinateClick}
            className="w-full h-full"
          />
        </div>

        {/* Settings panel - floating */}
        <div className="absolute top-4 right-4 z-10">
          <SettingsPanel
            settings={settings}
            onChange={handleSettingsChange}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onZoomFit={handleZoomFit}
            onZoomActual={handleZoomActual}
            onExportPNG={handleExportPNG}
            onExportFITS={handleExportFITS}
          />
        </div>

        {/* Coordinate display */}
        <CoordinateDisplay {...cursorCoords} />

        {/* Keyboard shortcuts hint */}
        <div className="absolute bottom-4 right-4 text-xs text-gray-500">
          <span className="bg-gray-800/80 px-2 py-1 rounded">
            Press <kbd className="font-mono">?</kbd> for shortcuts
          </span>
        </div>
      </div>
    </div>
  );
};

export default ImageViewerModal;
