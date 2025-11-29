import React, { useState } from "react";
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
  /** Enable format toggle button */
  allowFormatToggle?: boolean;
}

/**
 * Display astronomical coordinates in both HMS/DMS and decimal formats.
 * Optionally allows toggling between formats.
 */
const CoordinateDisplay: React.FC<CoordinateDisplayProps> = ({
  raDeg,
  decDeg,
  showDecimal = true,
  compact = false,
  label,
  allowFormatToggle = false,
}) => {
  const [showHMS, setShowHMS] = useState(true);
  
  const raHMS = formatRA(raDeg);
  const decDMS = formatDec(decDeg);

  if (compact) {
    return (
      <div className="font-mono text-sm">
        {label && <span className="text-gray-500 mr-2">{label}:</span>}
        {showHMS ? (
          <>
            <span className="text-gray-900">{raHMS}</span>
            <span className="text-gray-400 mx-1">,</span>
            <span className="text-gray-900">{decDMS}</span>
          </>
        ) : (
          <>
            <span className="text-gray-900">{formatDegrees(raDeg, 6)}</span>
            <span className="text-gray-400 mx-1">,</span>
            <span className="text-gray-900">{formatDegrees(decDeg, 6)}</span>
          </>
        )}
        {allowFormatToggle && (
          <button
            type="button"
            onClick={() => setShowHMS(!showHMS)}
            className="ml-2 text-xs text-blue-600 hover:text-blue-800"
            title={showHMS ? "Switch to decimal degrees" : "Switch to HMS/DMS"}
          >
            ↔
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {(label || allowFormatToggle) && (
        <div className="flex items-center justify-between">
          {label && <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>}
          {allowFormatToggle && (
            <button
              type="button"
              onClick={() => setShowHMS(!showHMS)}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
              title={showHMS ? "Switch to decimal degrees" : "Switch to HMS/DMS"}
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
              {showHMS ? "Decimal" : "HMS/DMS"}
            </button>
          )}
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        {/* RA */}
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Right Ascension</div>
          {showHMS ? (
            <>
              <div className="font-mono text-sm text-gray-900">{raHMS}</div>
              {showDecimal && (
                <div className="font-mono text-xs text-gray-500">{formatDegrees(raDeg, 6)}</div>
              )}
            </>
          ) : (
            <>
              <div className="font-mono text-sm text-gray-900">{formatDegrees(raDeg, 6)}</div>
              {showDecimal && (
                <div className="font-mono text-xs text-gray-500">{raHMS}</div>
              )}
            </>
          )}
        </div>
        {/* Dec */}
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Declination</div>
          {showHMS ? (
            <>
              <div className="font-mono text-sm text-gray-900">{decDMS}</div>
              {showDecimal && (
                <div className="font-mono text-xs text-gray-500">{formatDegrees(decDeg, 6)}</div>
              )}
            </>
          ) : (
            <>
              <div className="font-mono text-sm text-gray-900">{formatDegrees(decDeg, 6)}</div>
              {showDecimal && (
                <div className="font-mono text-xs text-gray-500">{decDMS}</div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CoordinateDisplay;
