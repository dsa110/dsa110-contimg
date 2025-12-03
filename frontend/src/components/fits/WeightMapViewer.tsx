import React, { useState, useCallback } from "react";
import FitsViewer from "./FitsViewer";
import Card from "../common/Card";

export interface WeightMapViewerProps {
  /** URL to the primary mosaic FITS file */
  mosaicUrl: string;
  /** URL to the weight map FITS file */
  weightMapUrl: string;
  /** Effective noise from the mosaic (Jy) */
  effectiveNoiseJy?: number;
  /** Number of images in the mosaic */
  nImages?: number;
  /** Median RMS of input images (Jy) */
  medianRmsJy?: number;
  /** Display ID for JS9 (must be unique per viewer) */
  displayId?: string;
  /** Width of the viewer */
  width?: number;
  /** Height of the viewer */
  height?: number;
  /** Optional class name */
  className?: string;
}

/**
 * Weight Map Viewer component for visualizing mosaic weight maps.
 *
 * Shows both the mosaic image and its associated weight map with
 * proper scaling and statistics display. The weight map represents
 * inverse-variance weights (1/σ²), so noise = 1/√weight at each pixel.
 *
 * Features:
 * - Toggle between mosaic and weight map views
 * - Statistics panel showing noise improvement
 * - Proper color scaling for weight maps (sqrt scale recommended)
 */
const WeightMapViewer: React.FC<WeightMapViewerProps> = ({
  mosaicUrl,
  weightMapUrl,
  effectiveNoiseJy,
  nImages,
  medianRmsJy,
  displayId = "WeightMapJS9",
  width = 512,
  height = 512,
  className = "",
}) => {
  const [viewMode, setViewMode] = useState<"mosaic" | "weights">("mosaic");

  // Calculate expected noise improvement
  const expectedNoiseJy =
    nImages && medianRmsJy ? medianRmsJy / Math.sqrt(nImages) : undefined;

  // Noise improvement factor
  const noiseImprovement = nImages ? Math.sqrt(nImages).toFixed(2) : undefined;

  // Check if effective noise matches expectation
  const noiseRatio =
    effectiveNoiseJy && expectedNoiseJy
      ? effectiveNoiseJy / expectedNoiseJy
      : undefined;

  const noiseMatchesExpected = noiseRatio
    ? noiseRatio > 0.7 && noiseRatio < 1.3
    : undefined;

  const handleViewToggle = useCallback(() => {
    setViewMode((prev) => (prev === "mosaic" ? "weights" : "mosaic"));
  }, []);

  const currentUrl = viewMode === "mosaic" ? mosaicUrl : weightMapUrl;

  const statsContent = (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
      {nImages !== undefined && (
        <div>
          <span className="text-gray-500">Images:</span>{" "}
          <span className="font-medium">{nImages}</span>
        </div>
      )}
      {medianRmsJy !== undefined && (
        <div>
          <span className="text-gray-500">Input RMS:</span>{" "}
          <span className="font-medium">
            {(medianRmsJy * 1e6).toFixed(1)} µJy
          </span>
        </div>
      )}
      {effectiveNoiseJy !== undefined && (
        <div>
          <span className="text-gray-500">Effective Noise:</span>{" "}
          <span className="font-medium">
            {(effectiveNoiseJy * 1e6).toFixed(1)} µJy
          </span>
        </div>
      )}
      {noiseImprovement && (
        <div>
          <span className="text-gray-500">Improvement:</span>{" "}
          <span className="font-medium">
            √{nImages} = {noiseImprovement}×
          </span>
        </div>
      )}
    </div>
  );

  const noiseValidation = noiseMatchesExpected !== undefined && (
    <div className="mb-3">
      {noiseMatchesExpected ? (
        <div className="text-xs text-green-700 bg-green-50 p-2 rounded border border-green-200">
          ✓ Effective noise matches √N expectation (ratio:{" "}
          {noiseRatio?.toFixed(2)})
        </div>
      ) : (
        <div className="text-xs text-yellow-700 bg-yellow-50 p-2 rounded border border-yellow-200">
          ⚠ Noise differs from √N expectation (ratio: {noiseRatio?.toFixed(2)})
          - may indicate non-uniform coverage or varying input quality
        </div>
      )}
    </div>
  );

  const toggleButton = (
    <button
      onClick={handleViewToggle}
      className={`px-3 py-1 text-sm rounded ${
        viewMode === "weights"
          ? "bg-blue-500 text-white"
          : "bg-gray-200 text-gray-700 hover:bg-gray-300"
      }`}
    >
      {viewMode === "mosaic" ? "Show Weights" : "Show Mosaic"}
    </button>
  );

  const viewBadge = (
    <span
      className={`ml-2 px-2 py-0.5 text-xs rounded ${
        viewMode === "mosaic"
          ? "bg-blue-100 text-blue-800"
          : "bg-purple-100 text-purple-800"
      }`}
    >
      {viewMode === "mosaic" ? "Mosaic" : "Weight Map"}
    </span>
  );

  return (
    <Card
      title="Mosaic Weight Map"
      subtitle={viewBadge}
      actions={toggleButton}
      className={className}
      padding="md"
    >
      {/* Stats Panel */}
      {(nImages || medianRmsJy || effectiveNoiseJy) && statsContent}
      {noiseValidation}

      {/* FITS Viewer */}
      <div className="relative">
        <FitsViewer
          fitsUrl={currentUrl}
          displayId={displayId}
          width={width}
          height={height}
          showControls={true}
        />

        {/* Weight map legend (shown when viewing weights) */}
        {viewMode === "weights" && (
          <div className="absolute bottom-4 right-4 bg-white/90 rounded-lg p-3 shadow-lg text-xs">
            <div className="font-medium mb-1">ℹ️ Weight Map</div>
            <div className="text-gray-500 space-y-0.5">
              <div>Weight = 1/σ² (inverse variance)</div>
              <div>Higher = better coverage</div>
              <div>Noise = 1/√weight</div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};

export default WeightMapViewer;
