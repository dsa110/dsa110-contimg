import React, { useState, useCallback, useMemo } from "react";
import { RangeSlider } from "../widgets";

export type FilterType = "range" | "select" | "checkbox" | "text" | "cone-search";

export interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

export interface FilterDefinition {
  id: string;
  label: string;
  type: FilterType;
  /** Group name for accordion sections */
  group?: string;
  /** For range filters */
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  histogram?: number[];
  /** For select/checkbox filters */
  options?: FilterOption[];
  /** For text filters */
  placeholder?: string;
}

export interface FilterValues {
  [filterId: string]: unknown;
}

export interface AdvancedFilterPanelProps {
  /** Filter definitions organized by group */
  filters: FilterDefinition[];
  /** Current filter values */
  values: FilterValues;
  /** Callback when filter values change */
  onChange: (values: FilterValues) => void;
  /** Callback to apply filters */
  onApply: () => void;
  /** Callback to reset all filters */
  onReset: () => void;
  /** Custom class name */
  className?: string;
}

interface ConeSearchValue {
  ra: string;
  dec: string;
  radius: string;
}

/**
 * Advanced filtering panel with accordion-style collapsible groups.
 * Supports range sliders, select dropdowns, checkboxes, text search, and cone search.
 */
const AdvancedFilterPanel: React.FC<AdvancedFilterPanelProps> = ({
  filters,
  values,
  onChange,
  onApply,
  onReset,
  className = "",
}) => {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(["all"]));

  // Group filters by their group property
  const groupedFilters = useMemo(() => {
    const groups: Record<string, FilterDefinition[]> = {};
    filters.forEach((filter) => {
      const group = filter.group || "General";
      if (!groups[group]) groups[group] = [];
      groups[group].push(filter);
    });
    return groups;
  }, [filters]);

  const toggleGroup = useCallback((group: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(group)) {
        next.delete(group);
      } else {
        next.add(group);
      }
      return next;
    });
  }, []);

  const handleFilterChange = useCallback(
    (filterId: string, value: unknown) => {
      onChange({
        ...values,
        [filterId]: value,
      });
    },
    [values, onChange]
  );

  // Count active filters
  const activeCount = useMemo(() => {
    let count = 0;
    Object.entries(values).forEach(([key, value]) => {
      const filter = filters.find((f) => f.id === key);
      if (!filter) return;

      if (filter.type === "range") {
        const rangeVal = value as { min: number; max: number };
        if (rangeVal && (rangeVal.min !== filter.min || rangeVal.max !== filter.max)) {
          count++;
        }
      } else if (filter.type === "checkbox") {
        if (Array.isArray(value) && value.length > 0) count++;
      } else if (filter.type === "cone-search") {
        const coneVal = value as ConeSearchValue;
        if (coneVal?.ra || coneVal?.dec || coneVal?.radius) count++;
      } else if (value) {
        count++;
      }
    });
    return count;
  }, [values, filters]);

  const renderFilter = (filter: FilterDefinition) => {
    switch (filter.type) {
      case "range": {
        const rangeValue = values[filter.id] as { min: number; max: number } | undefined;
        return (
          <RangeSlider
            min={filter.min ?? 0}
            max={filter.max ?? 100}
            step={filter.step}
            unit={filter.unit}
            minValue={rangeValue?.min}
            maxValue={rangeValue?.max}
            onChange={(minVal, maxVal) =>
              handleFilterChange(filter.id, { min: minVal, max: maxVal })
            }
            histogram={filter.histogram}
          />
        );
      }

      case "select":
        return (
          <select
            value={(values[filter.id] as string) || ""}
            onChange={(e) => handleFilterChange(filter.id, e.target.value)}
            className="form-select w-full"
          >
            <option value="">All</option>
            {filter.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
                {opt.count !== undefined && ` (${opt.count})`}
              </option>
            ))}
          </select>
        );

      case "checkbox":
        return (
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {filter.options?.map((opt) => (
              <label key={opt.value} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={((values[filter.id] as string[]) || []).includes(opt.value)}
                  onChange={(e) => {
                    const current = (values[filter.id] as string[]) || [];
                    const next = e.target.checked
                      ? [...current, opt.value]
                      : current.filter((v) => v !== opt.value);
                    handleFilterChange(filter.id, next);
                  }}
                  className="w-4 h-4 text-vast-green rounded border-gray-300 focus:ring-vast-green"
                />
                <span>{opt.label}</span>
                {opt.count !== undefined && <span className="text-gray-400">({opt.count})</span>}
              </label>
            ))}
          </div>
        );

      case "text":
        return (
          <input
            type="text"
            value={(values[filter.id] as string) || ""}
            onChange={(e) => handleFilterChange(filter.id, e.target.value)}
            placeholder={filter.placeholder || `Search ${filter.label.toLowerCase()}...`}
            className="form-control w-full"
          />
        );

      case "cone-search": {
        const coneValue = (values[filter.id] as ConeSearchValue) || {
          ra: "",
          dec: "",
          radius: "2",
        };
        return (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-500">RA (deg or HMS)</label>
                <input
                  type="text"
                  value={coneValue.ra}
                  onChange={(e) =>
                    handleFilterChange(filter.id, {
                      ...coneValue,
                      ra: e.target.value,
                    })
                  }
                  placeholder="180.0 or 12:00:00"
                  className="form-control w-full"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Dec (deg or DMS)</label>
                <input
                  type="text"
                  value={coneValue.dec}
                  onChange={(e) =>
                    handleFilterChange(filter.id, {
                      ...coneValue,
                      dec: e.target.value,
                    })
                  }
                  placeholder="+45.0 or +45:00:00"
                  className="form-control w-full"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500">Radius (arcmin)</label>
              <input
                type="number"
                value={coneValue.radius}
                onChange={(e) =>
                  handleFilterChange(filter.id, {
                    ...coneValue,
                    radius: e.target.value,
                  })
                }
                min={0.1}
                max={60}
                step={0.5}
                className="form-control w-full"
              />
            </div>
          </div>
        );
      }

      default:
        return null;
    }
  };

  return (
    <div className={`card ${className}`}>
      <div className="card-header flex items-center justify-between">
        <h4 className="text-lg font-semibold flex items-center gap-2">
          Filters
          {activeCount > 0 && <span className="badge badge-primary">{activeCount} active</span>}
        </h4>
        <button
          type="button"
          onClick={onReset}
          className="text-sm text-gray-500 hover:text-red-500"
        >
          Reset all
        </button>
      </div>

      <div className="divide-y divide-gray-200">
        {Object.entries(groupedFilters).map(([group, groupFilters]) => (
          <div key={group} className="accordion-group">
            {/* Accordion Header */}
            <button
              type="button"
              onClick={() => toggleGroup(group)}
              className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <span className="font-medium text-gray-700">{group}</span>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${
                  expandedGroups.has(group) ? "rotate-180" : ""
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {/* Accordion Content */}
            {expandedGroups.has(group) && (
              <div className="p-4 space-y-4">
                {groupFilters.map((filter) => (
                  <div key={filter.id} className="filter-item">
                    <label className="form-label">{filter.label}</label>
                    {renderFilter(filter)}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Apply Button */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <button type="button" onClick={onApply} className="btn btn-primary w-full">
          Apply Filters
        </button>
      </div>
    </div>
  );
};

export default AdvancedFilterPanel;
