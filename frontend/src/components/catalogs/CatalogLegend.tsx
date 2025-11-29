import React from "react";
import { CatalogDefinition } from "../../constants/catalogDefinitions";

export interface CatalogLegendProps {
  /** Enabled catalogs to display */
  catalogs: CatalogDefinition[];
  /** Custom class name */
  className?: string;
}

/**
 * Color-coded legend for catalog overlays.
 */
const CatalogLegend: React.FC<CatalogLegendProps> = ({
  catalogs,
  className = "",
}) => {
  if (catalogs.length === 0) return null;

  const renderSymbol = (catalog: CatalogDefinition) => {
    const size = 12;
    const style = { fill: catalog.color, stroke: catalog.color };

    switch (catalog.symbol) {
      case "circle":
        return (
          <svg width={size} height={size} viewBox="0 0 12 12">
            <circle cx="6" cy="6" r="5" {...style} fillOpacity={0.3} strokeWidth={1.5} />
          </svg>
        );
      case "square":
        return (
          <svg width={size} height={size} viewBox="0 0 12 12">
            <rect x="1" y="1" width="10" height="10" {...style} fillOpacity={0.3} strokeWidth={1.5} />
          </svg>
        );
      case "diamond":
        return (
          <svg width={size} height={size} viewBox="0 0 12 12">
            <polygon points="6,1 11,6 6,11 1,6" {...style} fillOpacity={0.3} strokeWidth={1.5} />
          </svg>
        );
      case "triangle":
        return (
          <svg width={size} height={size} viewBox="0 0 12 12">
            <polygon points="6,1 11,11 1,11" {...style} fillOpacity={0.3} strokeWidth={1.5} />
          </svg>
        );
      case "star":
        return (
          <svg width={size} height={size} viewBox="0 0 12 12">
            <polygon
              points="6,1 7.5,4.5 11,5 8.5,7.5 9,11 6,9 3,11 3.5,7.5 1,5 4.5,4.5"
              {...style}
              fillOpacity={0.3}
              strokeWidth={1}
            />
          </svg>
        );
      case "plus":
        return (
          <svg width={size} height={size} viewBox="0 0 12 12">
            <path d="M6,1 L6,11 M1,6 L11,6" stroke={catalog.color} strokeWidth={2} fill="none" />
          </svg>
        );
      case "cross":
        return (
          <svg width={size} height={size} viewBox="0 0 12 12">
            <path d="M1,1 L11,11 M11,1 L1,11" stroke={catalog.color} strokeWidth={2} fill="none" />
          </svg>
        );
      default:
        return (
          <span
            className="inline-block w-3 h-3 rounded-full"
            style={{ backgroundColor: catalog.color }}
          />
        );
    }
  };

  return (
    <div className={`flex flex-wrap gap-3 text-xs ${className}`}>
      {catalogs.map((catalog) => (
        <div
          key={catalog.id}
          className="flex items-center gap-1"
          title={catalog.description}
        >
          {renderSymbol(catalog)}
          <span style={{ color: catalog.color }}>{catalog.name}</span>
        </div>
      ))}
    </div>
  );
};

export default CatalogLegend;
