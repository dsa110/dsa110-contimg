import React, { useEffect, useRef, useState, useCallback } from "react";

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
  /** Optional source name for marker */
  sourceName?: string;
  /** Custom class name */
  className?: string;
  /** Enable fullscreen toggle */
  showFullscreen?: boolean;
}

declare global {
  interface Window {
    A?: {
      aladin: (element: HTMLElement, options: AladinOptions) => AladinInstance;
      catalogFromVizieR: (
        catalog: string,
        position: string,
        radius: number,
        options?: { shape?: string; color?: string }
      ) => void;
    };
  }
}

interface AladinOptions {
  target: string;
  fov: number;
  survey?: string;
  showReticle?: boolean;
  showZoomControl?: boolean;
  showFullscreenControl?: boolean;
  showLayersControl?: boolean;
  showGotoControl?: boolean;
  showShareControl?: boolean;
  showCatalog?: boolean;
  showFrame?: boolean;
}

interface AladinInstance {
  gotoRaDec: (ra: number, dec: number) => void;
  setFoV: (fov: number) => void;
  setImageSurvey: (survey: string) => void;
  addCatalog: (catalog: unknown) => void;
  increaseZoom: () => void;
  decreaseZoom: () => void;
  toggleFullscreen: () => void;
}

const ALADIN_CSS_URL = "https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.min.css";
const ALADIN_JS_URL = "https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.min.js";
const ALADIN_INTEGRITY = "sha384-5Fz016Wxf7jHEXNKZn3kQ2Ac9cnag6/VZw04/m+uxBUASk3G5i63DtAo0LikMIFm";

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

  // Load Aladin Lite scripts
  useEffect(() => {
    const loadAladinLite = async () => {
      // Check if already loaded
      if (window.A) {
        setIsLoading(false);
        return;
      }

      try {
        // Load CSS
        if (!document.querySelector(`link[href="${ALADIN_CSS_URL}"]`)) {
          const link = document.createElement("link");
          link.rel = "stylesheet";
          link.href = ALADIN_CSS_URL;
          link.integrity = ALADIN_INTEGRITY;
          link.crossOrigin = "anonymous";
          document.head.appendChild(link);
        }

        // Load JS
        if (!document.querySelector(`script[src="${ALADIN_JS_URL}"]`)) {
          await new Promise<void>((resolve, reject) => {
            const script = document.createElement("script");
            script.src = ALADIN_JS_URL;
            script.async = true;
            script.integrity = ALADIN_INTEGRITY;
            script.crossOrigin = "anonymous";
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Failed to load Aladin Lite"));
            document.head.appendChild(script);
          });
        }

        // Wait for A to be available
        let attempts = 0;
        while (!window.A && attempts < 50) {
          await new Promise((resolve) => setTimeout(resolve, 100));
          attempts++;
        }

        if (!window.A) {
          throw new Error("Aladin Lite failed to initialize");
        }

        setIsLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load sky viewer");
        setIsLoading(false);
      }
    };

    loadAladinLite();
  }, []);

  // Initialize Aladin viewer
  useEffect(() => {
    if (isLoading || error || !containerRef.current || !window.A) return;

    const target = `${raDeg.toFixed(6)} ${decDeg >= 0 ? "+" : ""}${decDeg.toFixed(6)}`;

    aladinRef.current = window.A.aladin(containerRef.current, {
      target,
      fov: currentFov,
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

    // Add marker at source position if name provided
    if (sourceName) {
      // Aladin will show the crosshair at center
    }
  }, [isLoading, error, raDeg, decDeg, currentFov, survey, showFullscreen, sourceName]);

  // Update position when coordinates change
  useEffect(() => {
    if (aladinRef.current) {
      aladinRef.current.gotoRaDec(raDeg, decDeg);
    }
  }, [raDeg, decDeg]);

  const handleZoomIn = useCallback(() => {
    if (aladinRef.current) {
      aladinRef.current.increaseZoom();
      setCurrentFov((prev) => Math.max(0.001, prev / 2));
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (aladinRef.current) {
      aladinRef.current.decreaseZoom();
      setCurrentFov((prev) => Math.min(180, prev * 2));
    }
  }, []);

  const handleFullscreen = useCallback(() => {
    if (aladinRef.current) {
      aladinRef.current.toggleFullscreen();
    }
  }, []);

  const heightStyle = typeof height === "number" ? `${height}px` : height;

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
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v12m6-6H6" />
          </svg>
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="bg-white/90 hover:bg-white p-1.5 rounded shadow text-gray-700 hover:text-gray-900 transition-colors"
          title="Zoom out"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 12H6" />
          </svg>
        </button>
        {showFullscreen && (
          <button
            type="button"
            onClick={handleFullscreen}
            className="bg-white/90 hover:bg-white p-1.5 rounded shadow text-gray-700 hover:text-gray-900 transition-colors"
            title="Toggle fullscreen"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
