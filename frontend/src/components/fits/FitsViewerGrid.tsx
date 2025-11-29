import React, { useState, useCallback, useEffect } from "react";
import FitsViewer from "./FitsViewer";

export interface FitsViewerGridProps {
  /** Array of FITS URLs to display */
  fitsUrls: string[];
  /** Number of columns in grid */
  columns?: 1 | 2 | 3 | 4;
  /** Size of each viewer */
  viewerSize?: number;
  /** Whether to synchronize pan/zoom across viewers */
  syncViews?: boolean;
  /** Labels for each panel */
  labels?: string[];
  /** Callback on coordinate click (with panel index) */
  onCoordinateClick?: (ra: number, dec: number, panelIndex: number) => void;
  /** Custom class name */
  className?: string;
}

/**
 * Grid layout for multiple synchronized FITS viewers.
 * Useful for comparing images at different frequencies or epochs.
 */
const FitsViewerGrid: React.FC<FitsViewerGridProps> = ({
  fitsUrls,
  columns = 2,
  viewerSize = 300,
  syncViews: initialSyncViews = true,
  labels,
  onCoordinateClick,
  className = "",
}) => {
  const [loadedCount, setLoadedCount] = useState(0);
  const [syncEnabled, setSyncEnabled] = useState(initialSyncViews);
  const [syncState, setSyncState] = useState<{
    zoom?: number;
    pan?: { x: number; y: number };
  }>({});

  // Handle sync across viewers
  const handleSync = useCallback(() => {
    if (!syncEnabled || !window.JS9) return;

    // Get state from first viewer
    const firstDisplayId = `JS9Grid_0`;
    try {
      const zoom = window.JS9.GetZoom({ display: firstDisplayId });
      const pan = window.JS9.GetPan({ display: firstDisplayId });

      if (zoom && pan) {
        // Apply to all other viewers
        for (let i = 1; i < fitsUrls.length; i++) {
          const displayId = `JS9Grid_${i}`;
          window.JS9.SetZoom(zoom, { display: displayId });
          window.JS9.SetPan(pan.x, pan.y, { display: displayId });
        }
      }
    } catch (err) {
      console.warn("Failed to sync views:", err);
    }
  }, [syncEnabled, fitsUrls.length]);

  // Set up sync event listeners
  useEffect(() => {
    if (!syncEnabled || loadedCount < fitsUrls.length) return;

    const handleChange = () => {
      handleSync();
    };

    // Set up callbacks on first viewer
    if (window.JS9) {
      window.JS9.SetCallback("onzoom", handleChange, { display: "JS9Grid_0" });
      window.JS9.SetCallback("onpan", handleChange, { display: "JS9Grid_0" });
    }

    return () => {
      if (window.JS9) {
        window.JS9.SetCallback("onzoom", null, { display: "JS9Grid_0" });
        window.JS9.SetCallback("onpan", null, { display: "JS9Grid_0" });
      }
    };
  }, [syncViews, loadedCount, fitsUrls.length, handleSync]);

  const handleLoad = () => {
    setLoadedCount((prev) => prev + 1);
  };

  const getGridClass = () => {
    switch (columns) {
      case 1:
        return "grid-cols-1";
      case 2:
        return "grid-cols-2";
      case 3:
        return "grid-cols-3";
      case 4:
        return "grid-cols-4";
      default:
        return "grid-cols-2";
    }
  };

  if (fitsUrls.length === 0) {
    return <div className="text-center text-gray-500 py-8">No FITS files to display</div>;
  }

  return (
    <div className={className}>
      {/* Header with sync toggle */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-600">
          {loadedCount}/{fitsUrls.length} images loaded
        </span>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={syncEnabled}
            onChange={(e) => setSyncEnabled(e.target.checked)}
            className="w-4 h-4 rounded accent-primary"
          />
          <span>Sync views</span>
        </label>
      </div>

      {/* Grid of viewers */}
      <div className={`grid ${getGridClass()} gap-4`}>
        {fitsUrls.map((url, index) => (
          <div key={`${url}-${index}`} className="relative">
            {/* Label */}
            {labels && labels[index] && (
              <div className="absolute top-2 left-2 z-10 bg-black/70 text-white text-xs px-2 py-1 rounded">
                {labels[index]}
              </div>
            )}

            {/* Viewer */}
            <FitsViewer
              fitsUrl={url}
              displayId={`JS9Grid_${index}`}
              width={viewerSize}
              height={viewerSize}
              showControls={false}
              onLoad={handleLoad}
              onCoordinateClick={
                onCoordinateClick ? (ra, dec) => onCoordinateClick(ra, dec, index) : undefined
              }
            />
          </div>
        ))}
      </div>

      {/* Shared controls */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Grid Controls:</span>
          <button
            onClick={() => {
              if (window.JS9) {
                for (let i = 0; i < fitsUrls.length; i++) {
                  window.JS9.SetZoom("tofit", { display: `JS9Grid_${i}` });
                }
              }
            }}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-100 transition-colors"
          >
            Fit All
          </button>
          <button
            onClick={() => {
              if (window.JS9) {
                for (let i = 0; i < fitsUrls.length; i++) {
                  window.JS9.SetZoom("in", { display: `JS9Grid_${i}` });
                }
              }
            }}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-100 transition-colors"
          >
            Zoom In All
          </button>
          <button
            onClick={() => {
              if (window.JS9) {
                for (let i = 0; i < fitsUrls.length; i++) {
                  window.JS9.SetZoom("out", { display: `JS9Grid_${i}` });
                }
              }
            }}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-100 transition-colors"
          >
            Zoom Out All
          </button>
          <select
            onChange={(e) => {
              if (window.JS9 && e.target.value) {
                for (let i = 0; i < fitsUrls.length; i++) {
                  window.JS9.SetColormap(e.target.value, {
                    display: `JS9Grid_${i}`,
                  });
                }
              }
            }}
            className="px-2 py-1 text-sm border border-gray-300 rounded"
            defaultValue=""
          >
            <option value="" disabled>
              Color map...
            </option>
            <option value="grey">Grey</option>
            <option value="heat">Heat</option>
            <option value="cool">Cool</option>
            <option value="viridis">Viridis</option>
            <option value="rainbow">Rainbow</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default FitsViewerGrid;
