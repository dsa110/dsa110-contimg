import React from "react";

export interface VariabilityControlsProps {
  /** Current η threshold */
  etaThreshold: number;
  /** Current V threshold */
  vThreshold: number;
  /** η sigma multiplier for dynamic threshold */
  etaSigma: number;
  /** V sigma multiplier for dynamic threshold */
  vSigma: number;
  /** Whether to use sigma-based thresholds */
  useSigmaThreshold: boolean;
  /** Min number of data points filter */
  minDataPoints: number;
  /** Color by field */
  colorBy: "variability" | "flux" | "measurements" | "none";
  /** Change handler */
  onChange: (values: Partial<VariabilityControlsValues>) => void;
}

export interface VariabilityControlsValues {
  etaThreshold: number;
  vThreshold: number;
  etaSigma: number;
  vSigma: number;
  useSigmaThreshold: boolean;
  minDataPoints: number;
  colorBy: "variability" | "flux" | "measurements" | "none";
}

/**
 * Controls panel for η-V plot customization.
 */
const VariabilityControls: React.FC<VariabilityControlsProps> = ({
  etaThreshold,
  vThreshold,
  etaSigma,
  vSigma,
  useSigmaThreshold,
  minDataPoints,
  colorBy,
  onChange,
}) => {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      {/* Threshold mode toggle */}
      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={useSigmaThreshold}
            onChange={(e) => onChange({ useSigmaThreshold: e.target.checked })}
            className="w-4 h-4 rounded"
          />
          <span className="text-sm">Use σ-based thresholds</span>
        </label>
        <p className="text-xs text-gray-500 mt-1">
          Calculate thresholds dynamically based on standard deviation
        </p>
      </div>

      {/* Sigma sliders (when sigma mode enabled) */}
      {useSigmaThreshold && (
        <div className="space-y-3 pl-2 border-l-2 border-primary">
          <div>
            <label className="flex items-center justify-between text-sm mb-1">
              <span>η threshold: {etaSigma}σ</span>
              <span className="text-gray-500 text-xs">above mean</span>
            </label>
            <input
              type="range"
              min={1}
              max={5}
              step={0.5}
              value={etaSigma}
              onChange={(e) => onChange({ etaSigma: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>
          <div>
            <label className="flex items-center justify-between text-sm mb-1">
              <span>V threshold: {vSigma}σ</span>
              <span className="text-gray-500 text-xs">above mean</span>
            </label>
            <input
              type="range"
              min={1}
              max={5}
              step={0.5}
              value={vSigma}
              onChange={(e) => onChange({ vSigma: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>
        </div>
      )}

      {/* Fixed threshold inputs (when sigma mode disabled) */}
      {!useSigmaThreshold && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm mb-1">η threshold</label>
            <input
              type="number"
              value={etaThreshold}
              onChange={(e) => onChange({ etaThreshold: parseFloat(e.target.value) || 0 })}
              step={0.1}
              className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">V threshold</label>
            <input
              type="number"
              value={vThreshold}
              onChange={(e) => onChange({ vThreshold: parseFloat(e.target.value) || 0 })}
              step={0.01}
              className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
            />
          </div>
        </div>
      )}

      {/* Min data points filter */}
      <div>
        <label className="block text-sm mb-1">Min data points: {minDataPoints}</label>
        <input
          type="range"
          min={2}
          max={20}
          value={minDataPoints}
          onChange={(e) => onChange({ minDataPoints: parseInt(e.target.value, 10) })}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
        />
        <div className="flex justify-between text-xs text-gray-400">
          <span>2</span>
          <span>20</span>
        </div>
      </div>

      {/* Color by selector */}
      <div>
        <label className="block text-sm mb-1">Color by</label>
        <select
          value={colorBy}
          onChange={(e) =>
            onChange({
              colorBy: e.target.value as VariabilityControlsValues["colorBy"],
            })
          }
          className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
        >
          <option value="variability">Variability (η × V)</option>
          <option value="flux">Peak Flux</option>
          <option value="measurements">N Measurements</option>
          <option value="none">No color gradient</option>
        </select>
      </div>
    </div>
  );
};

export default VariabilityControls;
