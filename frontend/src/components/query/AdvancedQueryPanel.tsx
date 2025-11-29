import React, { useState, useCallback, useMemo, useEffect } from "react";
import SesameResolver from "./SesameResolver";
import FluxFilters from "./FluxFilters";
import VariabilityFilters from "./VariabilityFilters";
import TagFilter from "./TagFilter";

export interface SourceQueryParams {
  // Cone search
  ra?: number;
  dec?: number;
  radius?: number;
  radiusUnit: "arcsec" | "arcmin" | "deg";
  coordFrame: "icrs" | "galactic";

  // Flux filters
  minFlux?: { min?: number; max?: number; type: "peak" | "int" };
  maxFlux?: { min?: number; max?: number; type: "peak" | "int" };
  avgFlux?: { min?: number; max?: number; type: "peak" | "int" };

  // Variability
  eta?: { min?: number; max?: number; type: "peak" | "int" };
  v?: { min?: number; max?: number; type: "peak" | "int" };
  vs?: { min?: number; max?: number; type: "peak" | "int" };
  m?: { min?: number; max?: number; type: "peak" | "int" };

  // SNR
  snrMin?: { min?: number; max?: number };
  snrMax?: { min?: number; max?: number };

  // Counts
  datapoints?: { min?: number; max?: number };
  selavy?: { min?: number; max?: number };
  forced?: { min?: number; max?: number };

  // Flags
  newSource?: boolean;
  noSiblings?: boolean;

  // Tags
  includeTags: string[];
  excludeTags: string[];

  // Pipeline run
  runName?: string;
}

export interface AdvancedQueryPanelProps {
  /** Available pipeline runs */
  runs?: { id: string; name: string }[];
  /** Available tags for filtering */
  availableTags?: string[];
  /** Callback when query is submitted */
  onSubmit: (params: SourceQueryParams) => void;
  /** Callback when query is reset */
  onReset?: () => void;
  /** Initial query params (e.g., from URL) */
  initialParams?: Partial<SourceQueryParams>;
  /** Custom class name */
  className?: string;
}

const DEFAULT_PARAMS: SourceQueryParams = {
  radiusUnit: "arcmin",
  coordFrame: "icrs",
  includeTags: [],
  excludeTags: [],
};

/**
 * Advanced source query panel with collapsible sections.
 * Inspired by VAST pipeline sources_query.html.
 */
const AdvancedQueryPanel: React.FC<AdvancedQueryPanelProps> = ({
  runs = [],
  availableTags = [],
  onSubmit,
  onReset,
  initialParams,
  className = "",
}) => {
  const [params, setParams] = useState<SourceQueryParams>({
    ...DEFAULT_PARAMS,
    ...initialParams,
  });
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["cone", "filters"])
  );

  // Sync URL hash with params
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (hash) {
      const urlParams: Partial<SourceQueryParams> = {};
      hash.split("&").forEach((param) => {
        const [key, value] = param.split("=");
        if (key && value) {
          if (key === "new_source") {
            urlParams.newSource = value === "true";
          } else if (key === "no_siblings") {
            urlParams.noSiblings = value === "true";
          } else if (key === "run_name") {
            urlParams.runName = decodeURIComponent(value);
          }
          // Add more URL param parsing as needed
        }
      });
      if (Object.keys(urlParams).length > 0) {
        setParams((prev) => ({ ...prev, ...urlParams }));
      }
    }
  }, []);

  const toggleSection = useCallback((section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);

  const handleConeSearchResolved = useCallback((ra: number, dec: number) => {
    setParams((prev) => ({ ...prev, ra, dec }));
  }, []);

  const handleReset = useCallback(() => {
    setParams({ ...DEFAULT_PARAMS });
    onReset?.();
  }, [onReset]);

  const handleSubmit = useCallback(() => {
    onSubmit(params);
  }, [params, onSubmit]);

  // Count active filters for badge
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (params.ra != null && params.dec != null) count++;
    if (params.minFlux?.min != null || params.minFlux?.max != null) count++;
    if (params.maxFlux?.min != null || params.maxFlux?.max != null) count++;
    if (params.avgFlux?.min != null || params.avgFlux?.max != null) count++;
    if (params.eta?.min != null || params.eta?.max != null) count++;
    if (params.v?.min != null || params.v?.max != null) count++;
    if (params.snrMin?.min != null || params.snrMin?.max != null) count++;
    if (params.snrMax?.min != null || params.snrMax?.max != null) count++;
    if (params.datapoints?.min != null || params.datapoints?.max != null) count++;
    if (params.newSource) count++;
    if (params.noSiblings) count++;
    if (params.includeTags.length > 0) count++;
    if (params.excludeTags.length > 0) count++;
    if (params.runName) count++;
    return count;
  }, [params]);

  const renderSection = (id: string, title: string, children: React.ReactNode) => {
    const isExpanded = expandedSections.has(id);
    return (
      <div className="border-b border-gray-200">
        <button
          onClick={() => toggleSection(id)}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <span className="font-semibold text-gray-700">{title}</span>
          <svg
            className={`w-5 h-5 text-gray-500 transition-transform ${
              isExpanded ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {isExpanded && <div className="p-4 space-y-4">{children}</div>}
      </div>
    );
  };

  return (
    <div className={`card ${className}`}>
      <div className="card-header flex items-center justify-between">
        <h4 className="text-lg font-semibold flex items-center gap-2">
          Source Query
          {activeFilterCount > 0 && (
            <span className="badge badge-primary">{activeFilterCount} filters</span>
          )}
        </h4>
        <button onClick={handleReset} className="text-sm text-gray-500 hover:text-red-500">
          Reset all
        </button>
      </div>

      <div className="divide-y divide-gray-200">
        {/* Data Source */}
        {renderSection(
          "source",
          "Data Source",
          <div className="form-group">
            <label className="form-label">Pipeline Run</label>
            <select
              value={params.runName || ""}
              onChange={(e) =>
                setParams((prev) => ({ ...prev, runName: e.target.value || undefined }))
              }
              className="form-select w-full"
            >
              <option value="">All Runs</option>
              {runs.map((run) => (
                <option key={run.id} value={run.name}>
                  {run.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Cone Search */}
        {renderSection(
          "cone",
          "Cone Search",
          <>
            <SesameResolver onResolved={handleConeSearchResolved} />

            <div className="grid grid-cols-2 gap-4">
              <div className="form-group">
                <label className="form-label">RA (deg or HMS)</label>
                <input
                  type="text"
                  value={params.ra ?? ""}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      ra: e.target.value ? parseFloat(e.target.value) : undefined,
                    }))
                  }
                  placeholder="180.0 or 12:00:00"
                  className="form-control"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Dec (deg or DMS)</label>
                <input
                  type="text"
                  value={params.dec ?? ""}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      dec: e.target.value ? parseFloat(e.target.value) : undefined,
                    }))
                  }
                  placeholder="+45.0 or +45:00:00"
                  className="form-control"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="form-group">
                <label className="form-label">Radius</label>
                <input
                  type="number"
                  value={params.radius ?? ""}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      radius: e.target.value ? parseFloat(e.target.value) : undefined,
                    }))
                  }
                  placeholder="2"
                  min={0}
                  step={0.1}
                  className="form-control"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Unit</label>
                <select
                  value={params.radiusUnit}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      radiusUnit: e.target.value as "arcsec" | "arcmin" | "deg",
                    }))
                  }
                  className="form-select"
                >
                  <option value="arcsec">arcsec</option>
                  <option value="arcmin">arcmin</option>
                  <option value="deg">deg</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Frame</label>
                <select
                  value={params.coordFrame}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      coordFrame: e.target.value as "icrs" | "galactic",
                    }))
                  }
                  className="form-select"
                >
                  <option value="icrs">ICRS</option>
                  <option value="galactic">Galactic</option>
                </select>
              </div>
            </div>
          </>
        )}

        {/* Flux Filters */}
        {renderSection(
          "flux",
          "Flux Filters",
          <FluxFilters
            values={{
              minFlux: params.minFlux,
              maxFlux: params.maxFlux,
              avgFlux: params.avgFlux,
            }}
            onChange={(fluxValues) => setParams((prev) => ({ ...prev, ...fluxValues }))}
          />
        )}

        {/* Variability Filters */}
        {renderSection(
          "variability",
          "Variability Metrics",
          <VariabilityFilters
            values={{
              eta: params.eta,
              v: params.v,
              vs: params.vs,
              m: params.m,
            }}
            onChange={(varValues) => setParams((prev) => ({ ...prev, ...varValues }))}
          />
        )}

        {/* SNR & Counts */}
        {renderSection(
          "snr",
          "SNR & Data Counts",
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="form-group">
                <label className="form-label">Min SNR</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    value={params.snrMin?.min ?? ""}
                    onChange={(e) =>
                      setParams((prev) => ({
                        ...prev,
                        snrMin: {
                          ...prev.snrMin,
                          min: e.target.value ? Number(e.target.value) : undefined,
                        },
                      }))
                    }
                    placeholder="Min"
                    className="form-control"
                  />
                  <input
                    type="number"
                    value={params.snrMin?.max ?? ""}
                    onChange={(e) =>
                      setParams((prev) => ({
                        ...prev,
                        snrMin: {
                          ...prev.snrMin,
                          max: e.target.value ? Number(e.target.value) : undefined,
                        },
                      }))
                    }
                    placeholder="Max"
                    className="form-control"
                  />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Max SNR</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    value={params.snrMax?.min ?? ""}
                    onChange={(e) =>
                      setParams((prev) => ({
                        ...prev,
                        snrMax: {
                          ...prev.snrMax,
                          min: e.target.value ? Number(e.target.value) : undefined,
                        },
                      }))
                    }
                    placeholder="Min"
                    className="form-control"
                  />
                  <input
                    type="number"
                    value={params.snrMax?.max ?? ""}
                    onChange={(e) =>
                      setParams((prev) => ({
                        ...prev,
                        snrMax: {
                          ...prev.snrMax,
                          max: e.target.value ? Number(e.target.value) : undefined,
                        },
                      }))
                    }
                    placeholder="Max"
                    className="form-control"
                  />
                </div>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Datapoints</label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  value={params.datapoints?.min ?? ""}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      datapoints: {
                        ...prev.datapoints,
                        min: e.target.value ? Number(e.target.value) : undefined,
                      },
                    }))
                  }
                  placeholder="Min"
                  min={1}
                  className="form-control"
                />
                <input
                  type="number"
                  value={params.datapoints?.max ?? ""}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      datapoints: {
                        ...prev.datapoints,
                        max: e.target.value ? Number(e.target.value) : undefined,
                      },
                    }))
                  }
                  placeholder="Max"
                  min={1}
                  className="form-control"
                />
              </div>
            </div>
          </div>
        )}

        {/* Source Type Flags */}
        {renderSection(
          "flags",
          "Source Type",
          <div className="space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={params.newSource || false}
                onChange={(e) => setParams((prev) => ({ ...prev, newSource: e.target.checked }))}
                className="w-4 h-4 text-vast-green rounded"
              />
              <span>New source</span>
              <span className="text-gray-400 text-sm">(appeared after first observation)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={params.noSiblings || false}
                onChange={(e) => setParams((prev) => ({ ...prev, noSiblings: e.target.checked }))}
                className="w-4 h-4 text-vast-green rounded"
              />
              <span>No siblings</span>
              <span className="text-gray-400 text-sm">(no multi-component islands)</span>
            </label>
          </div>
        )}

        {/* Tags */}
        {renderSection(
          "tags",
          "Tags",
          <TagFilter
            availableTags={availableTags}
            includeTags={params.includeTags}
            excludeTags={params.excludeTags}
            onIncludeChange={(tags) => setParams((prev) => ({ ...prev, includeTags: tags }))}
            onExcludeChange={(tags) => setParams((prev) => ({ ...prev, excludeTags: tags }))}
          />
        )}
      </div>

      {/* Action Buttons */}
      <div className="p-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-2">
        <button onClick={handleReset} className="btn btn-secondary">
          Reset
        </button>
        <button onClick={handleSubmit} className="btn btn-primary">
          Search
        </button>
      </div>
    </div>
  );
};

export default AdvancedQueryPanel;
