import React, { useEffect, useRef, useCallback, useState } from "react";
import FitsViewerControls, { FitsViewerControlsValues } from "./FitsViewerControls";
import type { JS9Image, JS9Region, JS9MouseEvent } from "../../types/js9.d";
import { VIEWER_TIMEOUTS } from "../../constants/astronomical";
import { logger } from "../../utils/logger";

// Note: JS9 global is declared in src/types/js9.d.ts

export interface FitsViewerProps {
  /** URL to FITS file */
  fitsUrl: string;
  /** Optional display ID for multiple viewers */
  displayId?: string;
  /** Width of the viewer */
  width?: number;
  /** Height of the viewer */
  height?: number;
  /** Whether to show controls panel */
  showControls?: boolean;
  /** Initial center coordinates (RA, Dec in degrees) */
  initialCenter?: { ra: number; dec: number };
  /** Initial field of view in arcminutes */
  initialFov?: number;
  /** Callback on coordinate click */
  onCoordinateClick?: (ra: number, dec: number) => void;
  /** Callback when image loads */
  onLoad?: () => void;
  /** Callback on error */
  onError?: (error: string) => void;
  /** Custom class name */
  className?: string;
}

/**
 * FITS image viewer using JS9 library.
 * Provides pan, zoom, color map, and scale controls.
 */
const FitsViewer: React.FC<FitsViewerProps> = ({
  fitsUrl,
  displayId = "JS9",
  width = 512,
  height = 512,
  showControls = true,
  initialCenter,
  initialFov,
  onCoordinateClick,
  onLoad,
  onError,
  className = "",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isJS9Ready, setIsJS9Ready] = useState(false);
  const [cursorWCS, setCursorWCS] = useState<{ ra: string; dec: string } | null>(null);
  const initialControlsRef = useRef<FitsViewerControlsValues | null>(null);

  // Control state
  const [controls, setControls] = useState<FitsViewerControlsValues>({
    colorMap: "grey",
    scale: "log",
    contrast: 0.5,
    bias: 0.5,
    showRegions: true,
    showCrosshair: false,
  });

  // Store initial controls to detect changes
  if (initialControlsRef.current === null) {
    initialControlsRef.current = { ...controls };
  }

  // Check if JS9 is loaded
  useEffect(() => {
    const checkJS9 = () => {
      if (window.JS9 && typeof window.JS9.Load === "function") {
        setIsJS9Ready(true);
        return true;
      }
      return false;
    };

    if (checkJS9()) return;

    // Poll for JS9 to load
    const interval = setInterval(() => {
      if (checkJS9()) {
        clearInterval(interval);
      }
    }, VIEWER_TIMEOUTS.JS9_POLL_INTERVAL_MS);

    // Timeout after configured duration
    const timeout = setTimeout(() => {
      clearInterval(interval);
      if (!isJS9Ready) {
        setError("JS9 library failed to load. Make sure JS9 CDN is included.");
        setIsLoading(false);
      }
    }, VIEWER_TIMEOUTS.JS9_LOAD_MS);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [isJS9Ready]);

  // Load FITS image
  useEffect(() => {
    if (!isJS9Ready || !fitsUrl) return;

    setIsLoading(true);
    setError(null);

    try {
      window.JS9.Load(fitsUrl, {
        display: displayId,
        onload: (_im: JS9Image) => {
          setIsLoading(false);

          // Apply initial settings
          if (initialCenter) {
            window.JS9.SetPan(initialCenter.ra, initialCenter.dec, {
              display: displayId,
            });
          }
          if (initialFov) {
            window.JS9.SetZoom("tofit", { display: displayId });
          }

          // Apply initial controls (from ref, not state to avoid dependency)
          const initControls = initialControlsRef.current;
          if (initControls) {
            window.JS9.SetColormap(initControls.colorMap, { display: displayId });
            window.JS9.SetScale(initControls.scale, { display: displayId });
          }

          onLoad?.();
        },
        onerror: (msg: string) => {
          setError(msg || "Failed to load FITS file");
          setIsLoading(false);
          onError?.(msg);
        },
      });

      // Set up click handler
      if (onCoordinateClick) {
        window.JS9.SetCallback(
          "onclick",
          (_im: JS9Image | null, _xreg: JS9Region | null, evt: JS9MouseEvent) => {
            const wcs = window.JS9.PixToWCS(evt.x, evt.y, { display: displayId });
            if (wcs) {
              onCoordinateClick(wcs.ra, wcs.dec);
            }
          },
          { display: displayId }
        );
      }

      // Set up mouse move handler for live WCS display
      window.JS9.SetCallback(
        "onmousemove",
        (_im: JS9Image | null, _xreg: JS9Region | null, evt: JS9MouseEvent) => {
          try {
            const wcs = window.JS9.PixToWCS(evt.x, evt.y, { display: displayId });
            if (wcs && wcs.ra !== undefined && wcs.dec !== undefined) {
              // Format as sexagesimal
              const raH = wcs.ra / 15;
              const raHours = Math.floor(raH);
              const raMin = Math.floor((raH - raHours) * 60);
              const raSec = ((raH - raHours) * 60 - raMin) * 60;
              const raStr = `${raHours.toString().padStart(2, "0")}:${raMin
                .toString()
                .padStart(2, "0")}:${raSec.toFixed(2).padStart(5, "0")}`;

              const decSign = wcs.dec >= 0 ? "+" : "-";
              const decAbs = Math.abs(wcs.dec);
              const decDeg = Math.floor(decAbs);
              const decMin = Math.floor((decAbs - decDeg) * 60);
              const decSec = ((decAbs - decDeg) * 60 - decMin) * 60;
              const decStr = `${decSign}${decDeg.toString().padStart(2, "0")}:${decMin
                .toString()
                .padStart(2, "0")}:${decSec.toFixed(1).padStart(4, "0")}`;

              setCursorWCS({ ra: raStr, dec: decStr });
            }
          } catch {
            // WCS may not be available
          }
        },
        { display: displayId }
      );
    } catch (err) {
      setError(String(err));
      setIsLoading(false);
      onError?.(String(err));
    }

    return () => {
      if (window.JS9?.CloseImage) {
        window.JS9.CloseImage({ display: displayId });
      }
    };
  }, [
    isJS9Ready,
    fitsUrl,
    displayId,
    initialCenter,
    initialFov,
    onLoad,
    onError,
    onCoordinateClick,
  ]);

  // Apply control changes
  useEffect(() => {
    if (!isJS9Ready || isLoading) return;

    try {
      window.JS9.SetColormap(controls.colorMap, { display: displayId });
      window.JS9.SetScale(controls.scale, { display: displayId });
      window.JS9.SetParam("contrast", controls.contrast, { display: displayId });
      window.JS9.SetParam("bias", controls.bias, { display: displayId });

      // Toggle regions visibility (hide/show, don't delete)
      // Use ChangeRegions to set visibility property
      try {
        const regions = window.JS9.GetRegions("all", { display: displayId });
        if (regions && regions.length > 0) {
          regions.forEach((region: JS9Region) => {
            window.JS9.ChangeRegions(
              region.id,
              {
                visibility: controls.showRegions,
              },
              { display: displayId }
            );
          });
        }
      } catch (regionErr) {
        // Regions may not exist yet or API differs
        console.debug("Region visibility toggle:", regionErr);
      }

      // Toggle crosshair
      window.JS9.SetParam("crosshair", controls.showCrosshair, { display: displayId });
    } catch (err) {
      logger.warn("Failed to apply JS9 settings", { error: err, displayId });
    }
  }, [controls, isJS9Ready, isLoading, displayId]);

  const handleZoomIn = useCallback(() => {
    if (window.JS9) {
      window.JS9.SetZoom("in", { display: displayId });
    }
  }, [displayId]);

  const handleZoomOut = useCallback(() => {
    if (window.JS9) {
      window.JS9.SetZoom("out", { display: displayId });
    }
  }, [displayId]);

  const handleZoomFit = useCallback(() => {
    if (window.JS9) {
      window.JS9.SetZoom("tofit", { display: displayId });
    }
  }, [displayId]);

  const handleExport = useCallback(
    (format: "png" | "fits") => {
      if (!window.JS9) return;

      if (format === "png") {
        window.JS9.SavePNG({ display: displayId });
      } else {
        window.JS9.SaveFITS({ display: displayId });
      }
    },
    [displayId]
  );

  const handleControlChange = (values: Partial<FitsViewerControlsValues>) => {
    setControls((prev) => ({ ...prev, ...values }));
  };

  return (
    <div className={`flex gap-4 ${className}`}>
      {/* Viewer area */}
      <div className="flex-1">
        <div
          ref={containerRef}
          className="relative bg-black rounded-lg overflow-hidden"
          style={{ width, height }}
        >
          {/* JS9 display div */}
          <div className="JS9" id={displayId} style={{ width: "100%", height: "100%" }} />

          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
              <div className="text-center">
                <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <span className="text-white text-sm">Loading FITS...</span>
              </div>
            </div>
          )}

          {/* Error overlay */}
          {error && (
            <div className="absolute inset-0 bg-red-900/80 flex items-center justify-center p-4">
              <div className="text-center">
                <svg
                  className="w-8 h-8 text-red-300 mx-auto mb-2"
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
                <p className="text-red-100 text-sm">{error}</p>
              </div>
            </div>
          )}

          {/* JS9 not loaded warning */}
          {!isJS9Ready && !isLoading && !error && (
            <div className="absolute inset-0 bg-gray-800 flex items-center justify-center p-4">
              <div className="text-center">
                <p className="text-gray-300 text-sm">
                  JS9 library not loaded. Add the following to your index.html:
                </p>
                <code className="text-xs text-gray-400 mt-2 block">
                  {'<script src="https://js9.si.edu/js9/js9.min.js"></script>'}
                </code>
              </div>
            </div>
          )}
        </div>

        {/* Coordinate display bar */}
        <div className="mt-2 flex justify-between items-center text-xs text-gray-500 bg-gray-100 rounded px-2 py-1">
          <span className="font-mono">
            {cursorWCS ? (
              <>
                <span className="text-gray-700">RA:</span> {cursorWCS.ra}{" "}
                <span className="text-gray-700 ml-2">Dec:</span> {cursorWCS.dec}
              </>
            ) : (
              <span className="text-gray-400">Move cursor over image for coordinates</span>
            )}
          </span>
          <span className="text-gray-400 truncate max-w-[150px]" title={fitsUrl}>
            {fitsUrl.split("/").pop()?.substring(0, 25) || "No file"}
          </span>
        </div>
      </div>

      {/* Controls panel */}
      {showControls && (
        <div className="w-48 flex-shrink-0">
          <FitsViewerControls
            {...controls}
            onChange={handleControlChange}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onZoomFit={handleZoomFit}
            onExport={handleExport}
          />
        </div>
      )}
    </div>
  );
};

export default FitsViewer;
