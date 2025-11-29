import React from "react";
import { formatRA, formatDec, formatDegrees } from "../../utils/coordinateFormatter";

export interface CoordinateDisplayProps {
  /** Right Ascension in decimal degrees */
  raDeg: number;
  /** Declination in decimal degrees */
  decDeg: number;
  /** Show decimal degrees alongside HMS/DMS */
  showDecimal?: boolean;
  /** Compact single-line display */
  compact?: boolean;
  /** Label for the coordinates */
  label?: string;
}

/**
 * Display astronomical coordinates in both HMS/DMS and decimal formats.
 */
const CoordinateDisplay: React.FC<CoordinateDisplayProps> = ({
  raDeg,
  decDeg,
  showDecimal = true,
  compact = false,
  label,
}) => {
  const raHMS = formatRA(raDeg);
  const decDMS = formatDec(decDeg);

  if (compact) {
    return (
      <div className="font-mono text-sm">
        {label && <span className="text-gray-500 mr-2">{label}:</span>}
        <span className="text-gray-900">{raHMS}</span>
        <span className="text-gray-400 mx-1">,</span>
        <span className="text-gray-900">{decDMS}</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {label && <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>}
      <div className="grid grid-cols-2 gap-4">
        {/* RA */}
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Right Ascension</div>
          <div className="font-mono text-sm text-gray-900">{raHMS}</div>
          {showDecimal && (
            <div className="font-mono text-xs text-gray-500">{formatDegrees(raDeg, 6)}</div>
          )}
        </div>
        {/* Dec */}
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Declination</div>
          <div className="font-mono text-sm text-gray-900">{decDMS}</div>
          {showDecimal && (
            <div className="font-mono text-xs text-gray-500">{formatDegrees(decDeg, 6)}</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CoordinateDisplay;
