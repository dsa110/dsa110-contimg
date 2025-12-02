import React, { useEffect, useRef, useState, useCallback } from "react";
// Import Aladin Lite from local npm package (v3.7.3-beta)
import A, { type AladinInstance } from "aladin-lite";

export interface AladinLiteViewerProps {
  /** Right Ascension in degrees */
  raDeg: number;
  /** Declination in degrees */
  decDeg: number;
  /** Field of view in degrees (default: 0.25) */
  fov?: number;
  /** Height of the viewer in pixels or CSS string */
  height?: number | string;
  /** Optional survey to display (default: P/DSS2/color) */
  survey?: string;
  /** Optional source name - displays a labeled marker at the target coordinates */
  sourceName?: string;
  /** Custom class name */
  className?: string;
  /** Enable fullscreen toggle */
  showFullscreen?: boolean;
}

/**
 * Interactive sky viewer using Aladin Lite v3.
 * Displays an interactive sky map centered on the specified coordinates.
 */
const AladinLiteViewer: React.FC<AladinLiteViewerProps> = ({
  raDeg,
  decDeg,
  fov = 0.25,
  height = 400,
  survey = "P/DSS2/color",
  sourceName,
  className = "",
  showFullscreen = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const aladinRef = useRef<AladinInstance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentFov, setCurrentFov] = useState(fov);
  const [shouldLoad, setShouldLoad] = useState(false);
  const currentFovRef = useRef(currentFov);
  const sourceNameRef = useRef(sourceName);

  const destroyInstance = useCallback(() => {
    if (aladinRef.current) {
      aladinRef.current.destroy();
      aladinRef.current = null;
    }
  }, []);

  useEffect(() => {
    currentFovRef.current = currentFov;
  }, [currentFov]);

  useEffect(() => {
    sourceNameRef.current = sourceName;
  }, [sourceName]);

  // Initialize Aladin viewer
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      if (!shouldLoad || error || !containerRef.current) return;

      const target = `${raDeg.toFixed(6)} ${
        decDeg >= 0 ? "+" : ""
      }${decDeg.toFixed(6)}`;

      try {
        setIsLoading(true);
        destroyInstance();

        // Initialize the Aladin Lite WASM module
        await A.init;

        if (cancelled) return;

        aladinRef.current = A.aladin(containerRef.current, {
          target,
          fov: currentFovRef.current,
          survey,
          showReticle: true,
          showZoomControl: true,
          showFullscreenControl: showFullscreen,
          showLayersControl: true,
          showGotoControl: false,
          showShareControl: false,
          showCatalog: true,
          showFrame: true,
        });

        // Add source marker if sourceName is provided
        if (sourceNameRef.current) {
          const catalog = A.catalog({
            name: "Source",
            sourceSize: 18,
            color: "#ff6b6b",
          });
          aladinRef.current.addCatalog(catalog);
          catalog.addSources([
            A.source(raDeg, decDeg, { name: sourceNameRef.current }),
          ]);
        }
        setIsLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load sky viewer"
          );
          setIsLoading(false);
        }
      }
    };

    init();

    return () => {
      cancelled = true;
      destroyInstance();
    };
  }, [
    destroyInstance,
    error,
    raDeg,
    decDeg,
    survey,
    showFullscreen,
    shouldLoad,
  ]);

  useEffect(() => {
    if (aladinRef.current) {
      aladinRef.current.gotoRaDec(raDeg, decDeg);
    }
  }, [raDeg, decDeg]);

  const handleZoomIn = useCallback(() => {
    if (aladinRef.current) {
      aladinRef.current.increaseZoom();
      setCurrentFov((prev) => {
        const next = Math.max(0.001, prev / 2);
        aladinRef.current?.setFoV(next);
        return next;
      });
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (aladinRef.current) {
      aladinRef.current.decreaseZoom();
      setCurrentFov((prev) => {
        const next = Math.min(180, prev * 2);
        aladinRef.current?.setFoV(next);
        return next;
      });
    }
  }, []);

  const handleFullscreen = useCallback(() => {
    if (aladinRef.current) {
      aladinRef.current.toggleFullscreen();
    }
  }, []);

  const heightStyle = typeof height === "number" ? `${height}px` : height;

  if (!shouldLoad) {
    return (
      <div
        className={`bg-gray-100 rounded-lg p-4 ${className}`}
        style={{ height: heightStyle }}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-gray-800">Sky Viewer</p>
            <p className="text-sm text-gray-600">
              Load the interactive Aladin viewer on demand to reduce initial
              page weight.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setShouldLoad(true)}
            aria-label="Load sky viewer"
          >
            Load viewer
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`bg-gray-100 rounded-lg flex items-center justify-center ${className}`}
        style={{ height: heightStyle }}
      >
        <div className="text-center text-gray-500 p-4">
          <svg
            className="w-12 h-12 mx-auto mb-2 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {isLoading && (
        <div
          className="absolute inset-0 bg-gray-100 rounded-lg flex items-center justify-center z-10"
          style={{ height: heightStyle }}
        >
          <div className="flex flex-col items-center text-gray-500">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2" />
            <span className="text-sm">Loading sky viewer...</span>
          </div>
        </div>
      )}
      <div
        ref={containerRef}
        className="rounded-lg overflow-hidden"
        style={{ height: heightStyle, width: "100%" }}
      />
      {/* Custom controls overlay */}
      <div className="absolute bottom-2 left-2 flex gap-1">
        <button
          type="button"
          onClick={handleZoomIn}
          className="bg-white/90 hover:bg-white p-1.5 rounded shadow text-gray-700 hover:text-gray-900 transition-colors"
          title="Zoom in"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6v12m6-6H6"
            />
          </svg>
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="bg-white/90 hover:bg-white p-1.5 rounded shadow text-gray-700 hover:text-gray-900 transition-colors"
          title="Zoom out"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18 12H6"
            />
          </svg>
        </button>
        {showFullscreen && (
          <button
            type="button"
            onClick={handleFullscreen}
            className="bg-white/90 hover:bg-white p-1.5 rounded shadow text-gray-700 hover:text-gray-900 transition-colors"
            title="Toggle fullscreen"
          >
            <svg
              className="w-4 h-4"
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
        )}
      </div>
      {/* Coordinate display */}
      <div className="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded font-mono">
        {raDeg.toFixed(4)}° {decDeg >= 0 ? "+" : ""}
        {decDeg.toFixed(4)}°
      </div>
    </div>
  );
};

export default AladinLiteViewer;
