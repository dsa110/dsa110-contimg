import React from "react";

export interface SourcePreviewProps {
  /** Source identifier */
  sourceId: string;
  /** Source name */
  name: string;
  /** RA coordinate (degrees) */
  ra: number;
  /** Dec coordinate (degrees) */
  dec: number;
  /** η value */
  eta: number;
  /** V value */
  v: number;
  /** Peak flux in mJy */
  peakFlux?: number;
  /** Number of measurements */
  nMeasurements?: number;
  /** Position for tooltip (screen coordinates) */
  position?: { x: number; y: number };
  /** Whether this is a hover preview or selected */
  isHover?: boolean;
  /** Click handler */
  onNavigate?: (sourceId: string) => void;
  /** Close handler */
  onClose?: () => void;
}

/**
 * Quick preview tooltip/card for source on η-V plot.
 */
const SourcePreview: React.FC<SourcePreviewProps> = ({
  sourceId,
  name,
  ra,
  dec,
  eta,
  v,
  peakFlux,
  nMeasurements,
  position,
  isHover = true,
  onNavigate,
  onClose,
}) => {
  const formatCoord = (value: number, isRa: boolean) => {
    if (isRa) {
      const hours = value / 15;
      const h = Math.floor(hours);
      const m = Math.floor((hours - h) * 60);
      const s = ((hours - h - m / 60) * 3600).toFixed(2);
      return `${h}h ${m}m ${s}s`;
    } else {
      const sign = value >= 0 ? "+" : "";
      const d = Math.floor(Math.abs(value));
      const m = Math.floor((Math.abs(value) - d) * 60);
      const s = ((Math.abs(value) - d - m / 60) * 3600).toFixed(1);
      return `${sign}${d}° ${m}' ${s}"`;
    }
  };

  const style: React.CSSProperties = position
    ? {
        position: "absolute",
        left: position.x + 10,
        top: position.y + 10,
        zIndex: 1000,
      }
    : {};

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg shadow-lg p-3 ${
        isHover ? "min-w-48" : "min-w-64"
      }`}
      style={style}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm text-gray-800 truncate">{name || sourceId}</span>
        {!isHover && onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            ×
          </button>
        )}
      </div>

      {/* Coordinates */}
      <div className="text-xs text-gray-500 mb-2">
        <div>RA: {formatCoord(ra, true)}</div>
        <div>Dec: {formatCoord(dec, false)}</div>
      </div>

      {/* Variability metrics */}
      <div className="flex gap-4 mb-2">
        <div className="text-center">
          <div className="text-lg font-semibold text-primary">{eta.toFixed(2)}</div>
          <div className="text-xs text-gray-500">η</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-semibold text-primary">{v.toFixed(3)}</div>
          <div className="text-xs text-gray-500">V</div>
        </div>
        {peakFlux !== undefined && (
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-700">{peakFlux.toFixed(2)}</div>
            <div className="text-xs text-gray-500">mJy</div>
          </div>
        )}
        {nMeasurements !== undefined && (
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-700">{nMeasurements}</div>
            <div className="text-xs text-gray-500">pts</div>
          </div>
        )}
      </div>

      {/* Action button */}
      {!isHover && onNavigate && (
        <button
          onClick={() => onNavigate(sourceId)}
          className="w-full text-sm bg-primary text-white py-1.5 rounded hover:bg-primary-dark transition-colors"
        >
          View Source Details
        </button>
      )}
    </div>
  );
};

export default SourcePreview;
