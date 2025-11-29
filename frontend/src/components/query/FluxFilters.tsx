import React from "react";

export interface FluxFiltersProps {
  /** Current filter values */
  values: {
    minFlux?: { min?: number; max?: number; type: "peak" | "int" };
    maxFlux?: { min?: number; max?: number; type: "peak" | "int" };
    avgFlux?: { min?: number; max?: number; type: "peak" | "int" };
  };
  /** Callback when values change */
  onChange: (values: FluxFiltersProps["values"]) => void;
  /** Custom class name */
  className?: string;
}

/**
 * Flux range filter inputs for min, max, and average flux.
 */
const FluxFilters: React.FC<FluxFiltersProps> = ({ values, onChange, className = "" }) => {
  const handleChange = (
    field: "minFlux" | "maxFlux" | "avgFlux",
    subfield: "min" | "max" | "type",
    value: string | number
  ) => {
    const current = values[field] || { type: "peak" as const };
    onChange({
      ...values,
      [field]: {
        ...current,
        [subfield]: subfield === "type" ? value : value === "" ? undefined : Number(value),
      },
    });
  };

  const renderFluxRow = (
    label: string,
    field: "minFlux" | "maxFlux" | "avgFlux",
    tooltip: string
  ) => {
    const current = values[field] || { type: "peak" as const };
    return (
      <div className="form-group">
        <div className="flex items-center gap-2 mb-1">
          <label className="form-label mb-0 font-semibold">{label}</label>
          <span className="text-gray-400 cursor-help" title={tooltip}>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <input
            type="number"
            value={current.min ?? ""}
            onChange={(e) => handleChange(field, "min", e.target.value)}
            placeholder="Min (mJy)"
            step="0.01"
            className="form-control"
          />
          <input
            type="number"
            value={current.max ?? ""}
            onChange={(e) => handleChange(field, "max", e.target.value)}
            placeholder="Max (mJy)"
            step="0.01"
            className="form-control"
          />
          <select
            value={current.type || "peak"}
            onChange={(e) => handleChange(field, "type", e.target.value)}
            className="form-select"
          >
            <option value="peak">Peak Flux</option>
            <option value="int">Int Flux</option>
          </select>
        </div>
      </div>
    );
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {renderFluxRow(
        "Min. Flux",
        "minFlux",
        "The minimum flux of a source. Peak or integrated flux can be selected."
      )}
      {renderFluxRow(
        "Max. Flux",
        "maxFlux",
        "The maximum flux of a source. Peak or integrated flux can be selected."
      )}
      {renderFluxRow(
        "Avg. Flux",
        "avgFlux",
        "The average flux of a source. Peak or integrated flux can be selected."
      )}
    </div>
  );
};

export default FluxFilters;
