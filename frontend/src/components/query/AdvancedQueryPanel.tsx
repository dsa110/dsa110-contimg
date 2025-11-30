import React, { useState, useCallback, useMemo, useEffect } from "react";
import SesameResolver from "./SesameResolver";
import FluxFilters from "./FluxFilters";
import VariabilityFilters from "./VariabilityFilters";
import TagFilter from "./TagFilter";
import { parseRA, parseDec } from "../../utils/coordinateParser";

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
  /** Disable internal URL hash syncing (use when parent manages URL state) */
  disableUrlSync?: boolean;
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
  disableUrlSync = false,
  className = "",
}) => {
  const [params, setParams] = useState<SourceQueryParams>({
    ...DEFAULT_PARAMS,
    ...initialParams,
  });
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["cone", "filters"])
  );
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [raInput, setRaInput] = useState<string>(initialParams?.ra?.toString() ?? "");
  const [decInput, setDecInput] = useState<string>(initialParams?.dec?.toString() ?? "");
  const debounceTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Parse URL hash into params
  const parseUrlHash = useCallback((): Partial<SourceQueryParams> => {
    const hash = window.location.hash.slice(1);
    if (!hash) return {};

    const urlParams: Partial<SourceQueryParams> = {};
    hash.split("&").forEach((param) => {
      const [key, value] = param.split("=");
      if (!key || !value) return;

      const decoded = decodeURIComponent(value);
      switch (key) {
        case "ra":
          urlParams.ra = parseFloat(decoded);
          break;
        case "dec":
          urlParams.dec = parseFloat(decoded);
          break;
        case "radius":
          urlParams.radius = parseFloat(decoded);
          break;
        case "radius_unit":
          if (["arcsec", "arcmin", "deg"].includes(decoded)) {
            urlParams.radiusUnit = decoded as "arcsec" | "arcmin" | "deg";
          }
          break;
        case "coord_frame":
          if (["icrs", "galactic"].includes(decoded)) {
            urlParams.coordFrame = decoded as "icrs" | "galactic";
          }
          break;
        case "new_source":
          urlParams.newSource = decoded === "true";
          break;
        case "no_siblings":
          urlParams.noSiblings = decoded === "true";
          break;
        case "run_name":
          urlParams.runName = decoded;
          break;
        case "include_tags":
          urlParams.includeTags = decoded.split(",").filter(Boolean);
          break;
        case "exclude_tags":
          urlParams.excludeTags = decoded.split(",").filter(Boolean);
          break;
        // Flux filters
        case "min_flux_min":
          urlParams.minFlux = { ...urlParams.minFlux, min: parseFloat(decoded), type: "peak" };
          break;
        case "min_flux_max":
          urlParams.minFlux = { ...urlParams.minFlux, max: parseFloat(decoded), type: "peak" };
          break;
        case "max_flux_min":
          urlParams.maxFlux = { ...urlParams.maxFlux, min: parseFloat(decoded), type: "peak" };
          break;
        case "max_flux_max":
          urlParams.maxFlux = { ...urlParams.maxFlux, max: parseFloat(decoded), type: "peak" };
          break;
        // Variability filters
        case "eta_min":
          urlParams.eta = { ...urlParams.eta, min: parseFloat(decoded), type: "peak" };
          break;
        case "eta_max":
          urlParams.eta = { ...urlParams.eta, max: parseFloat(decoded), type: "peak" };
          break;
        case "v_min":
          urlParams.v = { ...urlParams.v, min: parseFloat(decoded), type: "peak" };
          break;
        case "v_max":
          urlParams.v = { ...urlParams.v, max: parseFloat(decoded), type: "peak" };
          break;
      }
    });
    return urlParams;
  }, []);

  // Write params to URL hash
  const writeUrlHash = useCallback((params: SourceQueryParams) => {
    const parts: string[] = [];

    if (params.ra != null) parts.push(`ra=${params.ra.toFixed(6)}`);
    if (params.dec != null) parts.push(`dec=${params.dec.toFixed(6)}`);
    if (params.radius != null) parts.push(`radius=${params.radius}`);
    if (params.radiusUnit !== DEFAULT_PARAMS.radiusUnit) {
      parts.push(`radius_unit=${params.radiusUnit}`);
    }
    if (params.coordFrame !== DEFAULT_PARAMS.coordFrame) {
      parts.push(`coord_frame=${params.coordFrame}`);
    }
    if (params.newSource) parts.push("new_source=true");
    if (params.noSiblings) parts.push("no_siblings=true");
    if (params.runName) parts.push(`run_name=${encodeURIComponent(params.runName)}`);
    if (params.includeTags.length > 0) {
      parts.push(`include_tags=${params.includeTags.map(encodeURIComponent).join(",")}`);
    }
    if (params.excludeTags.length > 0) {
      parts.push(`exclude_tags=${params.excludeTags.map(encodeURIComponent).join(",")}`);
    }
    // Flux filters
    if (params.minFlux?.min != null) parts.push(`min_flux_min=${params.minFlux.min}`);
    if (params.minFlux?.max != null) parts.push(`min_flux_max=${params.minFlux.max}`);
    if (params.maxFlux?.min != null) parts.push(`max_flux_min=${params.maxFlux.min}`);
    if (params.maxFlux?.max != null) parts.push(`max_flux_max=${params.maxFlux.max}`);
    // Variability filters
    if (params.eta?.min != null) parts.push(`eta_min=${params.eta.min}`);
    if (params.eta?.max != null) parts.push(`eta_max=${params.eta.max}`);
    if (params.v?.min != null) parts.push(`v_min=${params.v.min}`);
    if (params.v?.max != null) parts.push(`v_max=${params.v.max}`);

    const newHash = parts.length > 0 ? `#${parts.join("&")}` : "";
    if (window.location.hash !== newHash) {
      window.history.replaceState(null, "", newHash || window.location.pathname);
    }
  }, []);

  // Validate params
  const validateParams = useCallback((params: SourceQueryParams): Record<string, string> => {
    const errors: Record<string, string> = {};

    // Coordinate validation
    if (params.ra != null && (params.ra < 0 || params.ra > 360)) {
      errors.ra = "RA must be between 0 and 360 degrees";
    }
    if (params.dec != null && (params.dec < -90 || params.dec > 90)) {
      errors.dec = "Dec must be between -90 and 90 degrees";
    }
    if (params.radius != null && params.radius < 0) {
      errors.radius = "Radius must be non-negative";
    }

    // Cone search completeness
    if (
      (params.ra != null || params.dec != null || params.radius != null) &&
      (params.ra == null || params.dec == null || params.radius == null)
    ) {
      if (params.ra == null) errors.ra = "RA required for cone search";
      if (params.dec == null) errors.dec = "Dec required for cone search";
      if (params.radius == null) errors.radius = "Radius required for cone search";
    }

    return errors;
  }, []);

  // Load from URL hash on mount (only if URL sync is enabled)
  useEffect(() => {
    if (disableUrlSync) return;
    const urlParams = parseUrlHash();
    if (Object.keys(urlParams).length > 0) {
      setParams((prev) => ({ ...prev, ...urlParams }));
    }
  }, [parseUrlHash, disableUrlSync]);

  // Sync with initialParams when they change (for controlled mode)
  // Extract primitive values to avoid object reference issues in deps
  const initRa = initialParams?.ra;
  const initDec = initialParams?.dec;
  const initRadius = initialParams?.radius;
  const initMinFluxMin = initialParams?.minFlux?.min;
  const initMaxFluxMax = initialParams?.maxFlux?.max;

  useEffect(() => {
    // Only sync if we have values to sync
    const updates: Partial<SourceQueryParams> = {};
    let hasUpdates = false;

    if (initRa !== undefined && initRa !== params.ra) {
      updates.ra = initRa;
      hasUpdates = true;
    }
    if (initDec !== undefined && initDec !== params.dec) {
      updates.dec = initDec;
      hasUpdates = true;
    }
    if (initRadius !== undefined && initRadius !== params.radius) {
      updates.radius = initRadius;
      hasUpdates = true;
    }
    if (initMinFluxMin !== undefined && initMinFluxMin !== params.minFlux?.min) {
      updates.minFlux = { min: initMinFluxMin, type: "peak" };
      hasUpdates = true;
    }
    if (initMaxFluxMax !== undefined && initMaxFluxMax !== params.maxFlux?.max) {
      updates.maxFlux = { max: initMaxFluxMax, type: "peak" };
      hasUpdates = true;
    }

    if (hasUpdates) {
      setParams((prev) => ({ ...prev, ...updates }));
    }

    // Sync input fields
    if (initRa !== undefined) {
      setRaInput(initRa?.toString() ?? "");
    }
    if (initDec !== undefined) {
      setDecInput(initDec?.toString() ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initRa, initDec, initRadius, initMinFluxMin, initMaxFluxMax]);

  // Debounced URL sync when params change (only if URL sync is enabled)
  useEffect(() => {
    if (disableUrlSync) {
      // Still validate even without URL sync
      setValidationErrors(validateParams(params));
      return;
    }

    if (debounceTimeoutRef.current) {
      window.clearTimeout(debounceTimeoutRef.current);
    }
    debounceTimeoutRef.current = window.setTimeout(() => {
      writeUrlHash(params);
      setValidationErrors(validateParams(params));
    }, 500);

    return () => {
      if (debounceTimeoutRef.current) {
        window.clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [params, writeUrlHash, validateParams, disableUrlSync]);

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
    setRaInput(ra.toFixed(6));
    setDecInput(dec.toFixed(6));
  }, []);

  const handleReset = useCallback(() => {
    setParams({ ...DEFAULT_PARAMS });
    setValidationErrors({});
    setRaInput("");
    setDecInput("");
    window.history.replaceState(null, "", window.location.pathname);
    onReset?.();
  }, [onReset]);

  const handleSubmit = useCallback(() => {
    const errors = validateParams(params);
    setValidationErrors(errors);
    if (Object.keys(errors).length === 0) {
      onSubmit(params);
    }
  }, [params, onSubmit, validateParams]);

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

  const hasValidationErrors = Object.keys(validationErrors).length > 0;

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
                  value={raInput}
                  onChange={(e) => {
                    const value = e.target.value;
                    setRaInput(value);
                    // Try to parse and update params
                    const parsed = parseRA(value);
                    setParams((prev) => ({
                      ...prev,
                      ra: parsed ?? undefined,
                    }));
                  }}
                  onBlur={() => {
                    // On blur, normalize to decimal if valid
                    if (params.ra != null) {
                      setRaInput(params.ra.toFixed(6));
                    }
                  }}
                  placeholder="180.0 or 12:00:00"
                  className={`form-control ${validationErrors.ra ? "border-red-500" : ""}`}
                />
                {validationErrors.ra && (
                  <p className="text-xs text-red-500 mt-1">{validationErrors.ra}</p>
                )}
              </div>
              <div className="form-group">
                <label className="form-label">Dec (deg or DMS)</label>
                <input
                  type="text"
                  value={decInput}
                  onChange={(e) => {
                    const value = e.target.value;
                    setDecInput(value);
                    // Try to parse and update params
                    const parsed = parseDec(value);
                    setParams((prev) => ({
                      ...prev,
                      dec: parsed ?? undefined,
                    }));
                  }}
                  onBlur={() => {
                    // On blur, normalize to decimal if valid
                    if (params.dec != null) {
                      setDecInput(params.dec.toFixed(6));
                    }
                  }}
                  placeholder="+45.0 or +45:00:00"
                  className={`form-control ${validationErrors.dec ? "border-red-500" : ""}`}
                />
                {validationErrors.dec && (
                  <p className="text-xs text-red-500 mt-1">{validationErrors.dec}</p>
                )}
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
                  className={`form-control ${validationErrors.radius ? "border-red-500" : ""}`}
                />
                {validationErrors.radius && (
                  <p className="text-xs text-red-500 mt-1">{validationErrors.radius}</p>
                )}
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

      {/* Validation Errors */}
      {hasValidationErrors && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200">
          <ul className="text-sm text-red-600 list-disc list-inside">
            {Object.entries(validationErrors).map(([field, error]) => (
              <li key={field}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Action Buttons */}
      <div className="p-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-2">
        <button onClick={handleReset} className="btn btn-secondary">
          Reset
        </button>
        <button
          onClick={handleSubmit}
          className={`btn btn-primary ${hasValidationErrors ? "opacity-75" : ""}`}
          disabled={hasValidationErrors}
        >
          Search
        </button>
      </div>
    </div>
  );
};

export default AdvancedQueryPanel;
