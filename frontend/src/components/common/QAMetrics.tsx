import React from "react";

export type QAGrade = "good" | "warn" | "fail" | null | undefined;

export interface QAMetricsProps {
  /** Overall QA grade */
  grade?: QAGrade;
  /** Summary text */
  summary?: string;
  /** RMS noise in Jy/beam */
  noiseJy?: number;
  /** Dynamic range */
  dynamicRange?: number;
  /** Beam major axis in arcsec */
  beamMajorArcsec?: number;
  /** Beam minor axis in arcsec */
  beamMinorArcsec?: number;
  /** Beam position angle in degrees */
  beamPaDeg?: number;
  /** Peak flux in Jy */
  peakFluxJy?: number;
  /** Compact display mode (single row) */
  compact?: boolean;
}

const gradeColors: Record<string, { bg: string; text: string; border: string }> = {
  good: { bg: "bg-green-50", text: "text-green-700", border: "border-green-200" },
  warn: { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200" },
  fail: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
};

const gradeIcons: Record<string, string> = {
  good: "✓",
  warn: "⚠",
  fail: "✗",
};

/**
 * Display QA metrics with visual indicators.
 */
const QAMetrics: React.FC<QAMetricsProps> = ({
  grade,
  summary,
  noiseJy,
  dynamicRange,
  beamMajorArcsec,
  beamMinorArcsec,
  beamPaDeg,
  peakFluxJy,
  compact = false,
}) => {
  const colors = grade
    ? gradeColors[grade]
    : { bg: "bg-gray-50", text: "text-gray-600", border: "border-gray-200" };
  const icon = grade ? gradeIcons[grade] : "?";

  // Format noise for display
  const formatNoise = (noise: number): string => {
    if (noise < 0.001) {
      return `${(noise * 1e6).toFixed(1)} μJy/beam`;
    } else if (noise < 1) {
      return `${(noise * 1e3).toFixed(2)} mJy/beam`;
    }
    return `${noise.toFixed(3)} Jy/beam`;
  };

  // Format flux for display
  const formatFlux = (flux: number): string => {
    if (Math.abs(flux) < 0.001) {
      return `${(flux * 1e6).toFixed(1)} μJy`;
    } else if (Math.abs(flux) < 1) {
      return `${(flux * 1e3).toFixed(2)} mJy`;
    }
    return `${flux.toFixed(3)} Jy`;
  };

  if (compact) {
    return (
      <div className="flex items-center gap-3 flex-wrap">
        {grade && (
          <span
            className={`badge ${
              grade === "good"
                ? "badge-success"
                : grade === "warn"
                ? "badge-warning"
                : "badge-error"
            }`}
          >
            {icon} {grade.toUpperCase()}
          </span>
        )}
        {noiseJy !== undefined && (
          <span className="text-sm text-gray-600">
            <span className="font-medium">σ:</span> {formatNoise(noiseJy)}
          </span>
        )}
        {dynamicRange !== undefined && (
          <span className="text-sm text-gray-600">
            <span className="font-medium">DR:</span> {dynamicRange.toFixed(0)}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} p-4`}>
      {/* Header with grade */}
      {grade && (
        <div className="flex items-center gap-2 mb-3">
          <span className={`text-2xl ${colors.text}`}>{icon}</span>
          <span className={`font-semibold ${colors.text} uppercase`}>{grade}</span>
          {summary && <span className="text-gray-600 text-sm ml-2">— {summary}</span>}
        </div>
      )}

      {/* Metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {noiseJy !== undefined && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">RMS Noise</div>
            <div className="font-mono text-sm">{formatNoise(noiseJy)}</div>
          </div>
        )}
        {dynamicRange !== undefined && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Dynamic Range</div>
            <div className="font-mono text-sm">{dynamicRange.toFixed(0)}:1</div>
          </div>
        )}
        {peakFluxJy !== undefined && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Peak Flux</div>
            <div className="font-mono text-sm">{formatFlux(peakFluxJy)}</div>
          </div>
        )}
        {beamMajorArcsec !== undefined && beamMinorArcsec !== undefined && (
          <div className="col-span-2 md:col-span-1">
            <div className="text-xs text-gray-500 uppercase tracking-wide">Beam Size</div>
            <div className="font-mono text-sm">
              {beamMajorArcsec.toFixed(1)}″ × {beamMinorArcsec.toFixed(1)}″
              {beamPaDeg !== undefined && (
                <span className="text-gray-500"> @ {beamPaDeg.toFixed(0)}°</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QAMetrics;
