import React, { useState, useCallback, useRef, useEffect } from "react";

export interface RangeSliderProps {
  /** Minimum possible value */
  min: number;
  /** Maximum possible value */
  max: number;
  /** Current minimum value */
  minValue?: number;
  /** Current maximum value */
  maxValue?: number;
  /** Step increment (default: 1) */
  step?: number;
  /** Label for the slider */
  label?: string;
  /** Unit suffix (e.g., "mJy", "deg") */
  unit?: string;
  /** Callback when values change */
  onChange?: (minValue: number, maxValue: number) => void;
  /** Callback when user finishes dragging (for debounced updates) */
  onChangeComplete?: (minValue: number, maxValue: number) => void;
  /** Show input fields for precise entry (default: true) */
  showInputs?: boolean;
  /** Show histogram overlay (optional) */
  histogram?: number[];
  /** Custom class name */
  className?: string;
  /** Number of decimal places for display */
  decimals?: number;
  /** Disabled state */
  disabled?: boolean;
  /** Format function for display values */
  formatValue?: (value: number) => string;
}

/**
 * Dual-handle range slider for min/max value filtering.
 * Supports precise input, histograms, and customizable formatting.
 */
const RangeSlider: React.FC<RangeSliderProps> = ({
  min,
  max,
  minValue: initialMinValue,
  maxValue: initialMaxValue,
  step = 1,
  label,
  unit = "",
  onChange,
  onChangeComplete,
  showInputs = true,
  histogram,
  className = "",
  decimals = 2,
  disabled = false,
  formatValue,
}) => {
  const [minValue, setMinValue] = useState(initialMinValue ?? min);
  const [maxValue, setMaxValue] = useState(initialMaxValue ?? max);
  const [isDragging, setIsDragging] = useState<"min" | "max" | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  // Update internal state when props change
  useEffect(() => {
    if (initialMinValue !== undefined) setMinValue(initialMinValue);
    if (initialMaxValue !== undefined) setMaxValue(initialMaxValue);
  }, [initialMinValue, initialMaxValue]);

  const formatDisplayValue = useCallback(
    (value: number): string => {
      if (formatValue) {
        return formatValue(value);
      }
      return value.toFixed(decimals);
    },
    [formatValue, decimals]
  );

  const getPercentage = useCallback(
    (value: number): number => {
      return ((value - min) / (max - min)) * 100;
    },
    [min, max]
  );

  const getValueFromPercentage = useCallback(
    (percentage: number): number => {
      const rawValue = min + (percentage / 100) * (max - min);
      // Snap to step
      const steppedValue = Math.round(rawValue / step) * step;
      return Math.max(min, Math.min(max, steppedValue));
    },
    [min, max, step]
  );

  const handleTrackClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (disabled || !trackRef.current) return;

      const rect = trackRef.current.getBoundingClientRect();
      const percentage = ((e.clientX - rect.left) / rect.width) * 100;
      const clickedValue = getValueFromPercentage(percentage);

      // Determine which handle to move (closest one)
      const distToMin = Math.abs(clickedValue - minValue);
      const distToMax = Math.abs(clickedValue - maxValue);

      if (distToMin <= distToMax) {
        const newMin = Math.min(clickedValue, maxValue - step);
        setMinValue(newMin);
        onChange?.(newMin, maxValue);
        onChangeComplete?.(newMin, maxValue);
      } else {
        const newMax = Math.max(clickedValue, minValue + step);
        setMaxValue(newMax);
        onChange?.(minValue, newMax);
        onChangeComplete?.(minValue, newMax);
      }
    },
    [disabled, getValueFromPercentage, minValue, maxValue, step, onChange, onChangeComplete]
  );

  const handleMinChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newMin = Math.min(parseFloat(e.target.value) || min, maxValue - step);
      setMinValue(newMin);
      onChange?.(newMin, maxValue);
    },
    [min, maxValue, step, onChange]
  );

  const handleMaxChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newMax = Math.max(parseFloat(e.target.value) || max, minValue + step);
      setMaxValue(newMax);
      onChange?.(minValue, newMax);
    },
    [max, minValue, step, onChange]
  );

  const handleInputBlur = useCallback(() => {
    onChangeComplete?.(minValue, maxValue);
  }, [minValue, maxValue, onChangeComplete]);

  const handleMinSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseFloat(e.target.value);
      const newMin = Math.min(value, maxValue - step);
      setMinValue(newMin);
      onChange?.(newMin, maxValue);
    },
    [maxValue, step, onChange]
  );

  const handleMaxSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseFloat(e.target.value);
      const newMax = Math.max(value, minValue + step);
      setMaxValue(newMax);
      onChange?.(minValue, newMax);
    },
    [minValue, step, onChange]
  );

  const handleSliderComplete = useCallback(() => {
    setIsDragging(null);
    onChangeComplete?.(minValue, maxValue);
  }, [minValue, maxValue, onChangeComplete]);

  const handleReset = useCallback(() => {
    setMinValue(min);
    setMaxValue(max);
    onChange?.(min, max);
    onChangeComplete?.(min, max);
  }, [min, max, onChange, onChangeComplete]);

  const minPercent = getPercentage(minValue);
  const maxPercent = getPercentage(maxValue);

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        {label && <span className="text-sm font-medium text-gray-700">{label}</span>}
        <button
          type="button"
          onClick={handleReset}
          disabled={disabled}
          className="text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-400"
        >
          Reset
        </button>
      </div>

      {/* Histogram overlay (optional) */}
      {histogram && histogram.length > 0 && (
        <div className="h-8 flex items-end gap-px">
          {histogram.map((value, index) => {
            const maxHist = Math.max(...histogram);
            const height = maxHist > 0 ? (value / maxHist) * 100 : 0;
            const barMin = min + (index / histogram.length) * (max - min);
            const barMax = min + ((index + 1) / histogram.length) * (max - min);
            const isInRange = barMax >= minValue && barMin <= maxValue;

            return (
              <div
                key={index}
                className={`flex-1 rounded-t transition-colors ${
                  isInRange ? "bg-blue-400" : "bg-gray-300"
                }`}
                style={{ height: `${height}%`, minHeight: value > 0 ? "2px" : "0" }}
              />
            );
          })}
        </div>
      )}

      {/* Slider track */}
      <div className="relative h-6 flex items-center">
        <div
          ref={trackRef}
          className="absolute w-full h-2 bg-gray-200 rounded-full cursor-pointer"
          onClick={handleTrackClick}
        >
          {/* Selected range */}
          <div
            className="absolute h-full bg-blue-500 rounded-full"
            style={{
              left: `${minPercent}%`,
              width: `${maxPercent - minPercent}%`,
            }}
          />
        </div>

        {/* Min handle */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={minValue}
          onChange={handleMinSliderChange}
          onMouseUp={handleSliderComplete}
          onTouchEnd={handleSliderComplete}
          onMouseDown={() => setIsDragging("min")}
          disabled={disabled}
          className="absolute w-full h-2 appearance-none bg-transparent pointer-events-none
            [&::-webkit-slider-thumb]:pointer-events-auto
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-5
            [&::-webkit-slider-thumb]:h-5
            [&::-webkit-slider-thumb]:bg-white
            [&::-webkit-slider-thumb]:border-2
            [&::-webkit-slider-thumb]:border-blue-500
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:shadow
            [&::-webkit-slider-thumb]:cursor-grab
            [&::-webkit-slider-thumb]:active:cursor-grabbing
            [&::-webkit-slider-thumb]:hover:scale-110
            [&::-webkit-slider-thumb]:transition-transform
            [&::-moz-range-thumb]:pointer-events-auto
            [&::-moz-range-thumb]:appearance-none
            [&::-moz-range-thumb]:w-5
            [&::-moz-range-thumb]:h-5
            [&::-moz-range-thumb]:bg-white
            [&::-moz-range-thumb]:border-2
            [&::-moz-range-thumb]:border-blue-500
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:shadow
            [&::-moz-range-thumb]:cursor-grab"
          style={{ zIndex: isDragging === "min" ? 2 : 1 }}
        />

        {/* Max handle */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={maxValue}
          onChange={handleMaxSliderChange}
          onMouseUp={handleSliderComplete}
          onTouchEnd={handleSliderComplete}
          onMouseDown={() => setIsDragging("max")}
          disabled={disabled}
          className="absolute w-full h-2 appearance-none bg-transparent pointer-events-none
            [&::-webkit-slider-thumb]:pointer-events-auto
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-5
            [&::-webkit-slider-thumb]:h-5
            [&::-webkit-slider-thumb]:bg-white
            [&::-webkit-slider-thumb]:border-2
            [&::-webkit-slider-thumb]:border-blue-500
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:shadow
            [&::-webkit-slider-thumb]:cursor-grab
            [&::-webkit-slider-thumb]:active:cursor-grabbing
            [&::-webkit-slider-thumb]:hover:scale-110
            [&::-webkit-slider-thumb]:transition-transform
            [&::-moz-range-thumb]:pointer-events-auto
            [&::-moz-range-thumb]:appearance-none
            [&::-moz-range-thumb]:w-5
            [&::-moz-range-thumb]:h-5
            [&::-moz-range-thumb]:bg-white
            [&::-moz-range-thumb]:border-2
            [&::-moz-range-thumb]:border-blue-500
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:shadow
            [&::-moz-range-thumb]:cursor-grab"
          style={{ zIndex: isDragging === "max" ? 2 : 1 }}
        />
      </div>

      {/* Value display / inputs */}
      {showInputs ? (
        <div className="flex items-center gap-2 text-sm">
          <div className="flex-1">
            <label className="sr-only">Minimum value</label>
            <div className="relative">
              <input
                type="number"
                min={min}
                max={maxValue - step}
                step={step}
                value={minValue}
                onChange={handleMinChange}
                onBlur={handleInputBlur}
                disabled={disabled}
                className="w-full px-2 py-1 pr-8 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
              {unit && (
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">
                  {unit}
                </span>
              )}
            </div>
          </div>
          <span className="text-gray-400">—</span>
          <div className="flex-1">
            <label className="sr-only">Maximum value</label>
            <div className="relative">
              <input
                type="number"
                min={minValue + step}
                max={max}
                step={step}
                value={maxValue}
                onChange={handleMaxChange}
                onBlur={handleInputBlur}
                disabled={disabled}
                className="w-full px-2 py-1 pr-8 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
              {unit && (
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">
                  {unit}
                </span>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex justify-between text-sm text-gray-600">
          <span>
            {formatDisplayValue(minValue)}
            {unit && ` ${unit}`}
          </span>
          <span>
            {formatDisplayValue(maxValue)}
            {unit && ` ${unit}`}
          </span>
        </div>
      )}
    </div>
  );
};

export default RangeSlider;
