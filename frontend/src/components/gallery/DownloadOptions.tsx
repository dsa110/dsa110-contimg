/**
 * Download Options Component
 *
 * Provides various download options for images including:
 * - Full FITS file download
 * - PNG preview with customizable settings
 * - Cutout extraction with region specification
 * - Batch download support
 */

import React, { useState, useCallback } from "react";
import { config } from "@/config";

// ============================================================================
// Types
// ============================================================================

export type ImageFormat = "fits" | "png" | "jpg" | "webp";
export type CutoutUnit = "arcsec" | "arcmin" | "deg" | "pixels";

export interface DownloadConfig {
  /** Output format */
  format: ImageFormat;
  /** PNG/image quality (0-100) for lossy formats */
  quality?: number;
  /** Colormap for PNG export */
  colormap?: string;
  /** Scale type for PNG export */
  scale?: string;
}

export interface CutoutConfig {
  /** Center RA in degrees */
  ra: number;
  /** Center Dec in degrees */
  dec: number;
  /** Width of cutout */
  width: number;
  /** Height of cutout */
  height: number;
  /** Unit for width/height */
  unit: CutoutUnit;
  /** Output format */
  format: ImageFormat;
}

export interface DownloadOptionsProps {
  /** Image ID to download */
  imageId: string;
  /** Image path/name for filename */
  imagePath: string;
  /** File size in bytes (for display) */
  fileSize?: number;
  /** Whether cutout is supported for this image */
  supportsCutout?: boolean;
  /** Default center coordinates (for cutout) */
  defaultRA?: number;
  defaultDec?: number;
  /** Button size variant */
  size?: "sm" | "md" | "lg";
  /** Display mode */
  mode?: "buttons" | "dropdown" | "menu";
  /** Callback on download start */
  onDownloadStart?: (config: DownloadConfig | CutoutConfig) => void;
  /** Callback on download complete */
  onDownloadComplete?: (success: boolean) => void;
  /** Additional CSS class */
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

const COLORMAPS = [
  "grey",
  "heat",
  "cool",
  "rainbow",
  "viridis",
  "plasma",
  "magma",
  "inferno",
];

const SCALES = ["linear", "log", "sqrt", "asinh", "histeq"];

const DEFAULT_CUTOUT_SIZE = 60; // arcseconds

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes >= 1e9) {
    return `${(bytes / 1e9).toFixed(2)} GB`;
  } else if (bytes >= 1e6) {
    return `${(bytes / 1e6).toFixed(2)} MB`;
  } else if (bytes >= 1e3) {
    return `${(bytes / 1e3).toFixed(2)} KB`;
  }
  return `${bytes} B`;
}

/**
 * Generate filename from path
 */
function generateFilename(
  path: string,
  format: ImageFormat,
  suffix?: string
): string {
  const baseName =
    path
      .split("/")
      .pop()
      ?.replace(/\.[^/.]+$/, "") ?? "image";
  const suffixPart = suffix ? `_${suffix}` : "";
  return `${baseName}${suffixPart}.${format}`;
}

// ============================================================================
// Icon Components
// ============================================================================

function DownloadIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function ChevronDownIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function CropIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6.13 1L6 16a2 2 0 0 0 2 2h15" />
      <path d="M1 6.13L16 6a2 2 0 0 1 2 2v15" />
    </svg>
  );
}

function ImageIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21 15 16 10 5 21" />
    </svg>
  );
}

// ============================================================================
// Sub-Components
// ============================================================================

interface PNGExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (colormap: string, scale: string, quality: number) => void;
}

function PNGExportDialog({ isOpen, onClose, onExport }: PNGExportDialogProps) {
  const [colormap, setColormap] = useState("grey");
  const [scale, setScale] = useState("log");
  const [quality, setQuality] = useState(90);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl p-6 w-80"
        onClick={(e) => e.stopPropagation()}
        data-testid="png-export-dialog"
      >
        <h3 className="text-lg font-semibold mb-4">Export as PNG</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Colormap
            </label>
            <select
              value={colormap}
              onChange={(e) => setColormap(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {COLORMAPS.map((cm) => (
                <option key={cm} value={cm}>
                  {cm.charAt(0).toUpperCase() + cm.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Scale
            </label>
            <select
              value={scale}
              onChange={(e) => setScale(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {SCALES.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Quality: {quality}%
            </label>
            <input
              type="range"
              min="10"
              max="100"
              value={quality}
              onChange={(e) => setQuality(parseInt(e.target.value, 10))}
              className="w-full"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onExport(colormap, scale, quality);
              onClose();
            }}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Export
          </button>
        </div>
      </div>
    </div>
  );
}

interface CutoutDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (config: CutoutConfig) => void;
  defaultRA: number;
  defaultDec: number;
}

function CutoutDialog({
  isOpen,
  onClose,
  onExport,
  defaultRA,
  defaultDec,
}: CutoutDialogProps) {
  const [ra, setRA] = useState(defaultRA);
  const [dec, setDec] = useState(defaultDec);
  const [width, setWidth] = useState(DEFAULT_CUTOUT_SIZE);
  const [height, setHeight] = useState(DEFAULT_CUTOUT_SIZE);
  const [unit, setUnit] = useState<CutoutUnit>("arcsec");
  const [format, setFormat] = useState<ImageFormat>("fits");

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl p-6 w-96"
        onClick={(e) => e.stopPropagation()}
        data-testid="cutout-dialog"
      >
        <h3 className="text-lg font-semibold mb-4">Extract Cutout</h3>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                RA (deg)
              </label>
              <input
                type="number"
                value={ra}
                onChange={(e) => setRA(parseFloat(e.target.value))}
                step="0.0001"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dec (deg)
              </label>
              <input
                type="number"
                value={dec}
                onChange={(e) => setDec(parseFloat(e.target.value))}
                step="0.0001"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Width
              </label>
              <input
                type="number"
                value={width}
                onChange={(e) => setWidth(parseFloat(e.target.value))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Height
              </label>
              <input
                type="number"
                value={height}
                onChange={(e) => setHeight(parseFloat(e.target.value))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Unit
            </label>
            <select
              value={unit}
              onChange={(e) => setUnit(e.target.value as CutoutUnit)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="arcsec">Arcseconds</option>
              <option value="arcmin">Arcminutes</option>
              <option value="deg">Degrees</option>
              <option value="pixels">Pixels</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Output Format
            </label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as ImageFormat)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="fits">FITS</option>
              <option value="png">PNG</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onExport({ ra, dec, width, height, unit, format });
              onClose();
            }}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Download Cutout
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function DownloadOptions({
  imageId,
  imagePath,
  fileSize,
  supportsCutout = true,
  defaultRA = 0,
  defaultDec = 0,
  size = "md",
  mode = "buttons",
  onDownloadStart,
  onDownloadComplete,
  className = "",
}: DownloadOptionsProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isPNGDialogOpen, setIsPNGDialogOpen] = useState(false);
  const [isCutoutDialogOpen, setIsCutoutDialogOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState<string | null>(null);

  // Size classes
  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  }[size];

  const iconSizeClass = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  }[size];

  // Download FITS
  const handleDownloadFITS = useCallback(async () => {
    setIsDownloading("fits");
    onDownloadStart?.({ format: "fits" });

    try {
      const url = `${config.api.baseUrl}/images/${imageId}/fits`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = generateFilename(imagePath, "fits");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);

      onDownloadComplete?.(true);
    } catch {
      onDownloadComplete?.(false);
    } finally {
      setIsDownloading(null);
    }
  }, [imageId, imagePath, onDownloadStart, onDownloadComplete]);

  // Download PNG
  const handleDownloadPNG = useCallback(
    async (colormap: string, scale: string, quality: number) => {
      setIsDownloading("png");
      onDownloadStart?.({ format: "png", quality, colormap, scale });

      try {
        const params = new URLSearchParams({
          colormap,
          scale,
          quality: quality.toString(),
        });
        const url = `${config.api.baseUrl}/images/${imageId}/png?${params}`;
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Download failed: ${response.statusText}`);
        }

        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = generateFilename(imagePath, "png");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(downloadUrl);

        onDownloadComplete?.(true);
      } catch {
        onDownloadComplete?.(false);
      } finally {
        setIsDownloading(null);
      }
    },
    [imageId, imagePath, onDownloadStart, onDownloadComplete]
  );

  // Download Cutout
  const handleDownloadCutout = useCallback(
    async (cutoutConfig: CutoutConfig) => {
      setIsDownloading("cutout");
      onDownloadStart?.(cutoutConfig);

      try {
        const params = new URLSearchParams({
          ra: cutoutConfig.ra.toString(),
          dec: cutoutConfig.dec.toString(),
          width: cutoutConfig.width.toString(),
          height: cutoutConfig.height.toString(),
          unit: cutoutConfig.unit,
          format: cutoutConfig.format,
        });
        const url = `${config.api.baseUrl}/images/${imageId}/cutout?${params}`;
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Download failed: ${response.statusText}`);
        }

        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = generateFilename(
          imagePath,
          cutoutConfig.format,
          "cutout"
        );
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(downloadUrl);

        onDownloadComplete?.(true);
      } catch {
        onDownloadComplete?.(false);
      } finally {
        setIsDownloading(null);
        setIsCutoutDialogOpen(false);
      }
    },
    [imageId, imagePath, onDownloadStart, onDownloadComplete]
  );

  // Render dropdown mode
  if (mode === "dropdown") {
    return (
      <div className={`relative inline-block ${className}`}>
        <button
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className={`
            inline-flex items-center gap-2
            rounded-md font-medium
            bg-blue-600 text-white
            hover:bg-blue-700
            transition-colors
            ${sizeClasses}
          `}
          data-testid="download-dropdown-button"
        >
          <DownloadIcon className={iconSizeClass} />
          <span>Download</span>
          <ChevronDownIcon className={iconSizeClass} />
        </button>

        {isDropdownOpen && (
          <div
            className="absolute right-0 mt-1 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-50"
            data-testid="download-dropdown-menu"
          >
            <div className="py-1">
              <button
                onClick={() => {
                  handleDownloadFITS();
                  setIsDropdownOpen(false);
                }}
                disabled={isDownloading !== null}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
              >
                <DownloadIcon className="w-4 h-4" />
                <span>FITS File</span>
                {fileSize && (
                  <span className="text-xs text-gray-400 ml-auto">
                    {formatFileSize(fileSize)}
                  </span>
                )}
              </button>
              <button
                onClick={() => {
                  setIsPNGDialogOpen(true);
                  setIsDropdownOpen(false);
                }}
                disabled={isDownloading !== null}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
              >
                <ImageIcon className="w-4 h-4" />
                <span>PNG Preview</span>
              </button>
              {supportsCutout && (
                <button
                  onClick={() => {
                    setIsCutoutDialogOpen(true);
                    setIsDropdownOpen(false);
                  }}
                  disabled={isDownloading !== null}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                >
                  <CropIcon className="w-4 h-4" />
                  <span>Cutout Region</span>
                </button>
              )}
            </div>
          </div>
        )}

        <PNGExportDialog
          isOpen={isPNGDialogOpen}
          onClose={() => setIsPNGDialogOpen(false)}
          onExport={handleDownloadPNG}
        />

        <CutoutDialog
          isOpen={isCutoutDialogOpen}
          onClose={() => setIsCutoutDialogOpen(false)}
          onExport={handleDownloadCutout}
          defaultRA={defaultRA}
          defaultDec={defaultDec}
        />
      </div>
    );
  }

  // Default: buttons mode
  return (
    <div
      className={`inline-flex flex-wrap gap-2 ${className}`}
      data-testid="download-options"
    >
      <button
        onClick={handleDownloadFITS}
        disabled={isDownloading !== null}
        className={`
          inline-flex items-center gap-2
          rounded-md font-medium
          transition-colors
          ${sizeClasses}
          ${
            isDownloading === "fits"
              ? "bg-blue-100 text-blue-600"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }
        `}
        data-testid="download-fits-button"
      >
        <DownloadIcon className={iconSizeClass} />
        <span>{isDownloading === "fits" ? "Downloading..." : "FITS"}</span>
        {fileSize && !isDownloading && (
          <span className="text-xs opacity-75">
            ({formatFileSize(fileSize)})
          </span>
        )}
      </button>

      <button
        onClick={() => setIsPNGDialogOpen(true)}
        disabled={isDownloading !== null}
        className={`
          inline-flex items-center gap-2
          rounded-md font-medium
          transition-colors
          ${sizeClasses}
          ${
            isDownloading === "png"
              ? "bg-green-100 text-green-600"
              : "bg-green-600 text-white hover:bg-green-700"
          }
        `}
        data-testid="download-png-button"
      >
        <ImageIcon className={iconSizeClass} />
        <span>{isDownloading === "png" ? "Exporting..." : "PNG"}</span>
      </button>

      {supportsCutout && (
        <button
          onClick={() => setIsCutoutDialogOpen(true)}
          disabled={isDownloading !== null}
          className={`
            inline-flex items-center gap-2
            rounded-md font-medium
            transition-colors
            ${sizeClasses}
            ${
              isDownloading === "cutout"
                ? "bg-purple-100 text-purple-600"
                : "bg-purple-600 text-white hover:bg-purple-700"
            }
          `}
          data-testid="download-cutout-button"
        >
          <CropIcon className={iconSizeClass} />
          <span>{isDownloading === "cutout" ? "Extracting..." : "Cutout"}</span>
        </button>
      )}

      <PNGExportDialog
        isOpen={isPNGDialogOpen}
        onClose={() => setIsPNGDialogOpen(false)}
        onExport={handleDownloadPNG}
      />

      <CutoutDialog
        isOpen={isCutoutDialogOpen}
        onClose={() => setIsCutoutDialogOpen(false)}
        onExport={handleDownloadCutout}
        defaultRA={defaultRA}
        defaultDec={defaultDec}
      />
    </div>
  );
}

export default DownloadOptions;
