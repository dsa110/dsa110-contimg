import React, { useState, useCallback, useEffect, useRef } from "react";
import { CATALOG_DEFINITIONS, CatalogDefinition } from "../../constants/catalogDefinitions";
import CatalogLegend from "./CatalogLegend";
import { queryCatalogCached, CatalogQueryResult, CatalogSource } from "../../utils/vizierQuery";

// Aladin types - using 'any' until proper npm types are available
// The aladin-lite module is loaded via vendor scripts, not npm
type AladinCatalog = any;
type AladinInstance = any;

export interface CatalogOverlayPanelProps {
  /** Currently enabled catalog IDs */
  enabledCatalogs: string[];
  /** Callback when catalog selection changes */
  onCatalogChange: (catalogIds: string[]) => void;
  /** Center RA in degrees (required for queries) */
  centerRa?: number;
  /** Center Dec in degrees (required for queries) */
  centerDec?: number;
  /** Search radius in arcminutes */
  searchRadius?: number;
  /** Callback with queried sources for overlay rendering */
  onSourcesLoaded?: (sources: Map<string, CatalogSource[]>) => void;
  /** Reference to Aladin Lite instance for overlay rendering */
  aladinRef?: React.RefObject<AladinInstance | null>;
  /** Custom class name */
  className?: string;
}

/**
 * Panel for toggling VizieR catalog overlays.
 * Queries VizieR TAP service and integrates with Aladin Lite for visualization.
 */
const CatalogOverlayPanel: React.FC<CatalogOverlayPanelProps> = ({
  enabledCatalogs,
  onCatalogChange,
  centerRa,
  centerDec,
  searchRadius = 5, // Default 5 arcmin
  onSourcesLoaded,
  aladinRef,
  className = "",
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [radiusInput, setRadiusInput] = useState(searchRadius);
  const [queryResults, setQueryResults] = useState<Map<string, CatalogQueryResult>>(new Map());
  const [loadingCatalogs, setLoadingCatalogs] = useState<Set<string>>(new Set());
  const [lastQueryRadius, setLastQueryRadius] = useState<number>(searchRadius);

  const abortControllerRef = useRef<AbortController | null>(null);
  const overlayLayersRef = useRef<Map<string, AladinCatalog>>(new Map());

  // Clear results when radius changes
  useEffect(() => {
    if (radiusInput !== lastQueryRadius) {
      setQueryResults(new Map());
      setLastQueryRadius(radiusInput);
    }
  }, [radiusInput, lastQueryRadius]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Query catalogs when selection or position changes
  useEffect(() => {
    if (centerRa === undefined || centerDec === undefined) return;
    if (enabledCatalogs.length === 0) {
      // Clear all overlays
      clearAllOverlays();
      setQueryResults(new Map());
      return;
    }

    // Abort previous queries
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    // Find catalogs that need querying
    const catalogsToQuery = enabledCatalogs.filter(
      (id) => !queryResults.has(id) || queryResults.get(id)?.error
    );

    if (catalogsToQuery.length === 0) return;

    setLoadingCatalogs((prev) => new Set([...prev, ...catalogsToQuery]));

    // Query each catalog
    catalogsToQuery.forEach(async (catalogId) => {
      const catalog = CATALOG_DEFINITIONS.find((c) => c.id === catalogId);
      if (!catalog) return;

      try {
        const result = await queryCatalogCached(catalog, centerRa, centerDec, radiusInput, signal);

        if (signal.aborted) return;

        setQueryResults((prev) => {
          const next = new Map(prev);
          next.set(catalogId, result);
          return next;
        });

        // Render overlay in Aladin if available
        if (aladinRef?.current && result.sources.length > 0) {
          renderCatalogOverlay(catalog, result.sources);
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        console.error(`Failed to query ${catalogId}:`, err);
      } finally {
        if (!signal.aborted) {
          setLoadingCatalogs((prev) => {
            const next = new Set(prev);
            next.delete(catalogId);
            return next;
          });
        }
      }
    });

    return () => {
      abortControllerRef.current?.abort();
    };
    // Note: clearAllOverlays and renderCatalogOverlay are stable due to useCallback.
    // queryResults is read but not a dep - we track what needs querying via the Set comparison.
    // aladinRef is a stable ref object.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabledCatalogs, centerRa, centerDec, radiusInput]);

  // Notify parent of loaded sources
  useEffect(() => {
    if (onSourcesLoaded) {
      const sourcesMap = new Map<string, CatalogSource[]>();
      queryResults.forEach((result, id) => {
        if (result.sources.length > 0) {
          sourcesMap.set(id, result.sources);
        }
      });
      onSourcesLoaded(sourcesMap);
    }
  }, [queryResults, onSourcesLoaded]);

  // Render catalog overlay in Aladin Lite
  const renderCatalogOverlay = useCallback(
    (catalog: CatalogDefinition, sources: CatalogSource[]) => {
      if (!aladinRef?.current) return;

      const aladin = aladinRef.current;

      // Remove existing layer for this catalog
      const existingLayer = overlayLayersRef.current.get(catalog.id);
      if (existingLayer) {
        aladin.removeCatalog(existingLayer);
      }

      // Create new catalog layer using Aladin's static A.catalog method
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const A = (window as any).A;
      const catalogLayer = A?.catalog({
        name: catalog.name,
        sourceSize: 12,
        color: catalog.color,
        shape:
          catalog.symbol === "circle"
            ? "circle"
            : catalog.symbol === "square"
            ? "square"
            : catalog.symbol === "diamond"
            ? "cross" // Use cross as substitute for rhomb (not in types)
            : "circle",
      });

      if (!catalogLayer) return;

      // Add sources to layer
      const aladinSources = sources.map((src) =>
        A.source(src.ra, src.dec, {
          name: src.id,
          catalog: catalog.name,
        })
      );
      catalogLayer.addSources(aladinSources);

      // Add layer to Aladin
      aladin.addCatalog(catalogLayer);
      overlayLayersRef.current.set(catalog.id, catalogLayer);
    },
    [aladinRef]
  );

  // Clear all overlays
  const clearAllOverlays = useCallback(() => {
    if (!aladinRef?.current) return;

    overlayLayersRef.current.forEach((layer) => {
      try {
        aladinRef.current?.removeCatalog(layer);
      } catch {
        // Layer may already be removed
      }
    });
    overlayLayersRef.current.clear();
  }, [aladinRef]);

  // Remove overlay when catalog is disabled
  useEffect(() => {
    overlayLayersRef.current.forEach((layer, catalogId) => {
      if (!enabledCatalogs.includes(catalogId) && aladinRef?.current) {
        try {
          aladinRef.current.removeCatalog(layer);
          overlayLayersRef.current.delete(catalogId);
        } catch {
          // Layer may already be removed
        }
      }
    });
  }, [enabledCatalogs, aladinRef]);

  const handleToggle = useCallback(
    (catalogId: string) => {
      if (enabledCatalogs.includes(catalogId)) {
        onCatalogChange(enabledCatalogs.filter((id) => id !== catalogId));
      } else {
        onCatalogChange([...enabledCatalogs, catalogId]);
      }
    },
    [enabledCatalogs, onCatalogChange]
  );

  const handleSelectAll = useCallback(() => {
    if (enabledCatalogs.length === CATALOG_DEFINITIONS.length) {
      onCatalogChange([]);
    } else {
      onCatalogChange(CATALOG_DEFINITIONS.map((c) => c.id));
    }
  }, [enabledCatalogs.length, onCatalogChange]);

  const enabledCatalogDefs = CATALOG_DEFINITIONS.filter((c) => enabledCatalogs.includes(c.id));
  const isLoading = loadingCatalogs.size > 0;

  // Group catalogs by type
  const opticalCatalogs = CATALOG_DEFINITIONS.filter((c) =>
    ["gaia", "tess", "ps1", "2mass", "wise"].includes(c.id)
  );
  const radioCatalogs = CATALOG_DEFINITIONS.filter((c) =>
    ["nvss", "first", "sumss", "racs", "vlass", "atnf"].includes(c.id)
  );

  const getResultCount = (catalogId: string): string | null => {
    const result = queryResults.get(catalogId);
    if (!result) return null;
    if (result.error) return "!";
    if (result.truncated) return `${result.count}+`;
    return result.count.toString();
  };

  const renderCatalogCheckbox = (catalog: CatalogDefinition) => {
    const resultCount = getResultCount(catalog.id);
    const isQuerying = loadingCatalogs.has(catalog.id);
    const hasError = queryResults.get(catalog.id)?.error;

    return (
      <label
        key={catalog.id}
        className="flex items-center gap-2 cursor-pointer text-sm hover:bg-gray-50 p-1 rounded"
        title={hasError || catalog.description}
      >
        <input
          type="checkbox"
          checked={enabledCatalogs.includes(catalog.id)}
          onChange={() => handleToggle(catalog.id)}
          className="w-4 h-4 rounded"
          style={{
            accentColor: catalog.color,
          }}
        />
        <span
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: catalog.color }}
        />
        <span className="flex-1">{catalog.name}</span>
        {isQuerying && (
          <span className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin" />
        )}
        {!isQuerying && resultCount && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${
              hasError ? "bg-red-100 text-red-600" : "bg-gray-100 text-gray-600"
            }`}
          >
            {resultCount}
          </span>
        )}
      </label>
    );
  };

  const hasCoordinates = centerRa !== undefined && centerDec !== undefined;

  return (
    <div className={`${className}`}>
      {/* Compact header with legend */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-gray-700">VizieR Catalogues</span>
          {isLoading && (
            <span className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}
          {enabledCatalogs.length > 0 && (
            <span className="badge badge-secondary text-xs">{enabledCatalogs.length}</span>
          )}
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          {isExpanded ? "Hide" : "Show"} options
        </button>
      </div>

      {/* Active catalog legend (always visible if any enabled) */}
      {enabledCatalogDefs.length > 0 && (
        <CatalogLegend catalogs={enabledCatalogDefs} className="mb-2" />
      )}

      {/* Expanded panel */}
      {isExpanded && (
        <div className="border border-gray-200 rounded-lg p-3 bg-white space-y-3">
          {/* Search radius input */}
          <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
            <label className="text-xs text-gray-600 whitespace-nowrap">Search radius:</label>
            <input
              type="number"
              min={0.5}
              max={60}
              step={0.5}
              value={radiusInput}
              onChange={(e) =>
                setRadiusInput(Math.max(0.5, Math.min(60, parseFloat(e.target.value) || 5)))
              }
              className="w-16 px-2 py-1 text-sm border border-gray-300 rounded"
            />
            <span className="text-xs text-gray-500">arcmin</span>
          </div>

          {!hasCoordinates && (
            <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
              Set center coordinates to query catalogs
            </div>
          )}

          {/* Quick actions */}
          <div className="flex justify-between items-center pb-2 border-b border-gray-100">
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              {enabledCatalogs.length === CATALOG_DEFINITIONS.length
                ? "Deselect all"
                : "Select all"}
            </button>
            <button
              type="button"
              onClick={() => {
                onCatalogChange([]);
                setQueryResults(new Map());
              }}
              className="text-xs text-gray-500 hover:text-red-500"
            >
              Clear
            </button>
          </div>

          {/* Optical/IR catalogs */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Optical / Infrared</p>
            <div className="grid grid-cols-2 gap-1">
              {opticalCatalogs.map(renderCatalogCheckbox)}
            </div>
          </div>

          {/* Radio catalogs */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Radio</p>
            <div className="grid grid-cols-2 gap-1">{radioCatalogs.map(renderCatalogCheckbox)}</div>
          </div>

          {/* Summary */}
          {queryResults.size > 0 && (
            <div className="text-xs text-gray-500 pt-2 border-t border-gray-100">
              {Array.from(queryResults.values()).reduce((sum, r) => sum + r.count, 0)} sources
              loaded
              {Array.from(queryResults.values()).some((r) => r.truncated) && " (some truncated)"}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CatalogOverlayPanel;
