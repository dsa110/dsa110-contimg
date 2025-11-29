import React, { useState, useCallback, useMemo } from "react";
import { RangeSlider } from "../widgets";

export interface FilterConfig {
  id: string;
  label: string;
  type: "range" | "select" | "checkbox" | "text";
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  options?: { value: string; label: string }[];
  defaultValue?: string | number | boolean | [number, number];
  histogram?: number[];
}

export interface FilterValues {
  [key: string]: string | number | boolean | [number, number] | undefined;
}

export interface FilterPanelProps {
  /** Filter configurations */
  filters: FilterConfig[];
  /** Current filter values */
  values: FilterValues;
  /** Callback when filters change */
  onChange: (values: FilterValues) => void;
  /** Title for the panel */
  title?: string;
  /** Collapsible sections */
  collapsible?: boolean;
  /** Initially collapsed */
  defaultCollapsed?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * Collapsible filter panel with support for range sliders, selects, and checkboxes.
 * Inspired by VASTER webapp's accordion filter design.
 */
const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  values,
  onChange,
  title = "Filters",
  collapsible = true,
  defaultCollapsed = false,
  className = "",
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const handleFilterChange = useCallback(
    (filterId: string, value: FilterValues[string]) => {
      onChange({ ...values, [filterId]: value });
    },
    [values, onChange]
  );

  const handleRangeChange = useCallback(
    (filterId: string, min: number, max: number) => {
      onChange({ ...values, [filterId]: [min, max] });
    },
    [values, onChange]
  );

  const handleReset = useCallback(() => {
    const resetValues: FilterValues = {};
    filters.forEach((filter) => {
      if (filter.defaultValue !== undefined) {
        resetValues[filter.id] = filter.defaultValue;
      }
    });
    onChange(resetValues);
  }, [filters, onChange]);

  const toggleSection = useCallback((sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId],
    }));
  }, []);

  const activeFilterCount = useMemo(() => {
    return Object.entries(values).filter(([key, value]) => {
      const filter = filters.find((f) => f.id === key);
      if (!filter) return false;

      if (filter.type === "range" && Array.isArray(value)) {
        return value[0] !== filter.min || value[1] !== filter.max;
      }

      if (filter.defaultValue !== undefined) {
        return value !== filter.defaultValue;
      }

      return value !== undefined && value !== "" && value !== false;
    }).length;
  }, [values, filters]);

  const renderFilter = (filter: FilterConfig) => {
    const value = values[filter.id];

    switch (filter.type) {
      case "range": {
        const rangeValue = Array.isArray(value) ? value : [filter.min ?? 0, filter.max ?? 100];
        return (
          <RangeSlider
            key={filter.id}
            min={filter.min ?? 0}
            max={filter.max ?? 100}
            step={filter.step ?? 1}
            minValue={rangeValue[0]}
            maxValue={rangeValue[1]}
            label={filter.label}
            unit={filter.unit}
            histogram={filter.histogram}
            onChange={(min, max) => handleRangeChange(filter.id, min, max)}
            showInputs={true}
          />
        );
      }

      case "select":
        return (
          <div key={filter.id} className="space-y-1">
            <label className="text-sm font-medium text-gray-700">{filter.label}</label>
            <select
              value={String(value ?? "")}
              onChange={(e) => handleFilterChange(filter.id, e.target.value || undefined)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All</option>
              {filter.options?.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        );

      case "checkbox":
        return (
          <label key={filter.id} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => handleFilterChange(filter.id, e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">{filter.label}</span>
          </label>
        );

      case "text":
        return (
          <div key={filter.id} className="space-y-1">
            <label className="text-sm font-medium text-gray-700">{filter.label}</label>
            <input
              type="text"
              value={String(value ?? "")}
              onChange={(e) => handleFilterChange(filter.id, e.target.value || undefined)}
              placeholder={`Filter by ${filter.label.toLowerCase()}...`}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}>
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-3 ${
          collapsible ? "cursor-pointer hover:bg-gray-50" : ""
        } ${!isCollapsed ? "border-b border-gray-200" : ""}`}
        onClick={collapsible ? () => setIsCollapsed(!isCollapsed) : undefined}
      >
        <div className="flex items-center gap-2">
          {collapsible && (
            <svg
              className={`w-4 h-4 text-gray-500 transition-transform ${
                isCollapsed ? "" : "rotate-90"
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          )}
          <h3 className="text-sm font-medium text-gray-900">{title}</h3>
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium text-blue-700 bg-blue-100 rounded-full">
              {activeFilterCount}
            </span>
          )}
        </div>
        {!isCollapsed && activeFilterCount > 0 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleReset();
            }}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Reset all
          </button>
        )}
      </div>

      {/* Filter content */}
      {!isCollapsed && (
        <div className="p-4 space-y-4">{filters.map((filter) => renderFilter(filter))}</div>
      )}
    </div>
  );
};

export default FilterPanel;
