import React, { useState, useCallback } from "react";
import { CATALOG_DEFINITIONS, CatalogDefinition } from "../../constants/catalogDefinitions";
import CatalogLegend from "./CatalogLegend";

export interface CatalogOverlayPanelProps {
  /** Currently enabled catalog IDs */
  enabledCatalogs: string[];
  /** Callback when catalog selection changes */
  onCatalogChange: (catalogIds: string[]) => void;
  /** Whether overlays are loading */
  isLoading?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * Panel for toggling VizieR catalog overlays.
 * Integrates with Aladin Lite for visualization.
 */
const CatalogOverlayPanel: React.FC<CatalogOverlayPanelProps> = ({
  enabledCatalogs,
  onCatalogChange,
  isLoading = false,
  className = "",
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

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

  // Group catalogs by type
  const opticalCatalogs = CATALOG_DEFINITIONS.filter((c) =>
    ["gaia", "tess", "ps1", "2mass", "wise"].includes(c.id)
  );
  const radioCatalogs = CATALOG_DEFINITIONS.filter((c) =>
    ["nvss", "first", "sumss", "racs", "vlass", "atnf"].includes(c.id)
  );

  const renderCatalogCheckbox = (catalog: CatalogDefinition) => (
    <label
      key={catalog.id}
      className="flex items-center gap-2 cursor-pointer text-sm hover:bg-gray-50 p-1 rounded"
      title={catalog.description}
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
      <span>{catalog.name}</span>
    </label>
  );

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
          {/* Quick actions */}
          <div className="flex justify-between items-center pb-2 border-b border-gray-100">
            <button onClick={handleSelectAll} className="text-xs text-blue-600 hover:text-blue-800">
              {enabledCatalogs.length === CATALOG_DEFINITIONS.length
                ? "Deselect all"
                : "Select all"}
            </button>
            <button
              onClick={() => onCatalogChange([])}
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
        </div>
      )}
    </div>
  );
};

export default CatalogOverlayPanel;
