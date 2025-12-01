import React, { useState, useCallback } from "react";
import { config } from "../../config";

/**
 * X-axis options for the raster plot.
 */
export type RasterXAxis = "time" | "baseline" | "frequency";

/**
 * Y-axis (visibility component) options.
 */
export type RasterYAxis = "amp" | "phase" | "real" | "imag";

interface MsRasterPlotProps {
  /** Full path to the Measurement Set */
  msPath: string;
  /** Initial X-axis dimension */
  initialXAxis?: RasterXAxis;
  /** Initial Y-axis (visibility component) */
  initialYAxis?: RasterYAxis;
  /** Initial colormap */
  initialColormap?: string;
  /** Plot width in pixels */
  width?: number;
  /** Plot height in pixels */
  height?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Axis label mappings for display.
 */
const X_AXIS_LABELS: Record<RasterXAxis, string> = {
  time: "Time",
  baseline: "Baseline",
  frequency: "Frequency",
};

const Y_AXIS_LABELS: Record<RasterYAxis, string> = {
  amp: "Amplitude",
  phase: "Phase",
  real: "Real",
  imag: "Imaginary",
};

/**
 * Available colormaps.
 */
const COLORMAPS = [
  "viridis",
  "plasma",
  "inferno",
  "magma",
  "cividis",
  "coolwarm",
  "RdBu",
  "Spectral",
];

/**
 * Visibility raster plot component for Measurement Sets.
 *
 * Displays a 2D raster plot of visibility data from an MS file.
 * Users can select the X-axis (time, baseline, or frequency) and
 * the visibility component to plot (amplitude, phase, real, or imaginary).
 *
 * The plot is generated server-side and returned as a PNG image.
 */
const MsRasterPlot: React.FC<MsRasterPlotProps> = ({
  msPath,
  initialXAxis = "time",
  initialYAxis = "amp",
  initialColormap = "viridis",
  width = 800,
  height = 600,
  className = "",
}) => {
  const [xaxis, setXAxis] = useState<RasterXAxis>(initialXAxis);
  const [yaxis, setYAxis] = useState<RasterYAxis>(initialYAxis);
  const [colormap, setColormap] = useState<string>(initialColormap);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [imageKey, setImageKey] = useState<number>(0);

  /**
   * Build the URL for the raster plot image.
   */
  const buildImageUrl = useCallback(() => {
    const encodedPath = encodeURIComponent(msPath);
    const params = new URLSearchParams({
      xaxis,
      yaxis,
      colormap,
      width: width.toString(),
      height: height.toString(),
    });
    return `${config.api.baseUrl}/ms/${encodedPath}/raster?${params.toString()}`;
  }, [msPath, xaxis, yaxis, colormap, width, height]);

  /**
   * Handle image load success.
   */
  const handleImageLoad = useCallback(() => {
    setIsLoading(false);
    setError(null);
  }, []);

  /**
   * Handle image load error.
   */
  const handleImageError = useCallback(() => {
    setIsLoading(false);
    setError("Failed to load visibility plot. The MS may be invalid or inaccessible.");
  }, []);

  /**
   * Refresh the plot (force re-fetch).
   */
  const handleRefresh = useCallback(() => {
    setIsLoading(true);
    setError(null);
    setImageKey((prev) => prev + 1);
  }, []);

  /**
   * Handle axis change.
   */
  const handleXAxisChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setXAxis(e.target.value as RasterXAxis);
    setIsLoading(true);
    setError(null);
  }, []);

  const handleYAxisChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setYAxis(e.target.value as RasterYAxis);
    setIsLoading(true);
    setError(null);
  }, []);

  const handleColormapChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setColormap(e.target.value);
    setIsLoading(true);
    setError(null);
  }, []);

  return (
    <div className={`ms-raster-plot ${className}`}>
      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-4 items-center">
        {/* X-axis selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="xaxis-select" className="text-sm font-medium text-gray-700">
            X-Axis:
          </label>
          <select
            id="xaxis-select"
            value={xaxis}
            onChange={handleXAxisChange}
            className="block rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
          >
            {(Object.keys(X_AXIS_LABELS) as RasterXAxis[]).map((axis) => (
              <option key={axis} value={axis}>
                {X_AXIS_LABELS[axis]}
              </option>
            ))}
          </select>
        </div>

        {/* Y-axis selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="yaxis-select" className="text-sm font-medium text-gray-700">
            Component:
          </label>
          <select
            id="yaxis-select"
            value={yaxis}
            onChange={handleYAxisChange}
            className="block rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
          >
            {(Object.keys(Y_AXIS_LABELS) as RasterYAxis[]).map((axis) => (
              <option key={axis} value={axis}>
                {Y_AXIS_LABELS[axis]}
              </option>
            ))}
          </select>
        </div>

        {/* Colormap selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="colormap-select" className="text-sm font-medium text-gray-700">
            Colormap:
          </label>
          <select
            id="colormap-select"
            value={colormap}
            onChange={handleColormapChange}
            className="block rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
          >
            {COLORMAPS.map((cmap) => (
              <option key={cmap} value={cmap}>
                {cmap}
              </option>
            ))}
          </select>
        </div>

        {/* Refresh button */}
        <button
          type="button"
          onClick={handleRefresh}
          disabled={isLoading}
          className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Refresh plot"
        >
          <svg
            className={`w-4 h-4 mr-1.5 ${isLoading ? "animate-spin" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </button>
      </div>

      {/* Plot container */}
      <div
        className="relative bg-gray-100 rounded-lg overflow-hidden"
        style={{ minHeight: height, maxWidth: width }}
      >
        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-75 z-10">
            <div className="flex flex-col items-center">
              <svg
                className="animate-spin h-8 w-8 text-blue-600"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span className="mt-2 text-sm text-gray-600">Generating plot...</span>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-red-50 z-10">
            <div className="text-center p-4">
              <svg
                className="mx-auto h-10 w-10 text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="mt-2 text-sm text-red-600">{error}</p>
              <button
                type="button"
                onClick={handleRefresh}
                className="mt-3 text-sm text-blue-600 hover:text-blue-800"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {/* Plot image */}
        <img
          key={imageKey}
          src={buildImageUrl()}
          alt={`Visibility ${Y_AXIS_LABELS[yaxis]} vs ${X_AXIS_LABELS[xaxis]}`}
          onLoad={handleImageLoad}
          onError={handleImageError}
          className={`block max-w-full h-auto ${isLoading || error ? "invisible" : ""}`}
          style={{ maxHeight: height }}
        />
      </div>

      {/* Plot description */}
      <p className="mt-2 text-xs text-gray-500">
        Showing {Y_AXIS_LABELS[yaxis].toLowerCase()} vs {X_AXIS_LABELS[xaxis].toLowerCase()}.
        Data averaged over polarizations.
      </p>
    </div>
  );
};

export default MsRasterPlot;
