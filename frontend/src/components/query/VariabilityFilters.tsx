import React from "react";

export interface VariabilityFiltersProps {
  /** Current filter values */
  values: {
    eta?: { min?: number; max?: number; type: "peak" | "int" };
    v?: { min?: number; max?: number; type: "peak" | "int" };
    vs?: { min?: number; max?: number; type: "peak" | "int" };
    m?: { min?: number; max?: number; type: "peak" | "int" };
  };
  /** Callback when values change */
  onChange: (values: VariabilityFiltersProps["values"]) => void;
  /** Custom class name */
  className?: string;
}

/**
 * Variability metric filter inputs (η, V, Vs, m).
 */
const VariabilityFilters: React.FC<VariabilityFiltersProps> = ({
  values,
  onChange,
  className = "",
}) => {
  const handleChange = (
    field: "eta" | "v" | "vs" | "m",
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

  const renderMetricRow = (
    label: string,
    field: "eta" | "v" | "vs" | "m",
    tooltip: string,
    showType: boolean = true
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
        <div className={`grid ${showType ? "grid-cols-3" : "grid-cols-2"} gap-2`}>
          <input
            type="number"
            value={current.min ?? ""}
            onChange={(e) => handleChange(field, "min", e.target.value)}
            placeholder="Min"
            step="0.01"
            className="form-control"
          />
          <input
            type="number"
            value={current.max ?? ""}
            onChange={(e) => handleChange(field, "max", e.target.value)}
            placeholder="Max"
            step="0.01"
            className="form-control"
          />
          {showType && (
            <select
              value={current.type || "peak"}
              onChange={(e) => handleChange(field, "type", e.target.value)}
              className="form-select"
            >
              <option value="peak">Peak Flux</option>
              <option value="int">Int Flux</option>
            </select>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {renderMetricRow(
        "η (Eta) Metric",
        "eta",
        "The weighted reduced chi-squared variability metric. Higher values indicate more variability."
      )}
      {renderMetricRow(
        "V Metric",
        "v",
        "The variability index, equivalent to fractional variability. V = σ/μ."
      )}
      {renderMetricRow(
        "Max |Vs| Metric",
        "vs",
        "The maximum two-epoch variability t-statistic value derived from the source."
      )}
      {renderMetricRow(
        "Max |m| Metric",
        "m",
        "The maximum two-epoch modulation index derived from the source (measure of variability)."
      )}
    </div>
  );
};

export default VariabilityFilters;
