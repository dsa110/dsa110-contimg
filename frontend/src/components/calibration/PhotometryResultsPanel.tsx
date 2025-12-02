/**
 * Photometry Results Panel Component
 *
 * Displays photometry results with flux ratios and astrometric offsets.
 */

import React from "react";
import type {
  PhotometryResult,
  QualityThresholds,
} from "../../types/calibration";
import { DEFAULT_QUALITY_THRESHOLDS } from "../../types/calibration";

interface PhotometryResultsPanelProps {
  photometry: PhotometryResult;
  expectedFlux?: number;
  thresholds?: Partial<QualityThresholds>;
  className?: string;
}

function getFluxRatioStatus(
  ratio: number,
  min: number,
  max: number
): "good" | "warning" | "critical" {
  if (ratio >= min && ratio <= max) return "good";
  const deviation = Math.max(
    Math.abs(ratio - min) / (1 - min),
    Math.abs(ratio - max) / (max - 1)
  );
  if (deviation > 0.5) return "critical";
  return "warning";
}

function getPositionStatus(
  offset: number,
  maxOffset: number
): "good" | "warning" | "critical" {
  if (offset <= maxOffset * 0.5) return "good";
  if (offset <= maxOffset) return "warning";
  return "critical";
}

const statusColors = {
  good: "text-green-600 dark:text-green-400",
  warning: "text-yellow-600 dark:text-yellow-400",
  critical: "text-red-600 dark:text-red-400",
};

const statusBgColors = {
  good: "bg-green-100 dark:bg-green-900/30",
  warning: "bg-yellow-100 dark:bg-yellow-900/30",
  critical: "bg-red-100 dark:bg-red-900/30",
};

export function PhotometryResultsPanel({
  photometry,
  expectedFlux,
  thresholds = {},
  className = "",
}: PhotometryResultsPanelProps) {
  const mergedThresholds = { ...DEFAULT_QUALITY_THRESHOLDS, ...thresholds };

  const fluxRatio =
    photometry.flux_ratio ??
    (expectedFlux ? photometry.peak_flux_jy / expectedFlux : undefined);

  const fluxRatioStatus = fluxRatio
    ? getFluxRatioStatus(
        fluxRatio,
        mergedThresholds.min_flux_ratio,
        mergedThresholds.max_flux_ratio
      )
    : "good";

  const positionStatus = photometry.position_offset_arcsec
    ? getPositionStatus(
        photometry.position_offset_arcsec,
        mergedThresholds.max_position_offset_arcsec
      )
    : "good";

  const snrStatus: "good" | "warning" | "critical" =
    photometry.snr >= mergedThresholds.min_snr * 2
      ? "good"
      : photometry.snr >= mergedThresholds.min_snr
      ? "warning"
      : "critical";

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Photometry Results
      </h3>

      {/* Main metrics grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Peak Flux */}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Peak Flux
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-gray-100 mt-1">
            {photometry.peak_flux_jy.toFixed(3)}
            <span className="text-sm font-normal ml-1">Jy</span>
          </div>
        </div>

        {/* Integrated Flux */}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Integrated Flux
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-gray-100 mt-1">
            {photometry.integrated_flux_jy.toFixed(3)}
            <span className="text-sm font-normal ml-1">Jy</span>
          </div>
        </div>

        {/* RMS */}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            RMS Noise
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-gray-100 mt-1">
            {(photometry.rms_jy * 1000).toFixed(2)}
            <span className="text-sm font-normal ml-1">mJy</span>
          </div>
        </div>

        {/* SNR */}
        <div className={`rounded-lg p-3 ${statusBgColors[snrStatus]}`}>
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            SNR
          </div>
          <div className={`text-xl font-bold mt-1 ${statusColors[snrStatus]}`}>
            {photometry.snr.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Flux ratio and position offset */}
      {(fluxRatio !== undefined ||
        photometry.position_offset_arcsec !== undefined) && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 gap-4">
            {/* Flux Ratio */}
            {fluxRatio !== undefined && (
              <div
                className={`rounded-lg p-3 ${statusBgColors[fluxRatioStatus]}`}
              >
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Flux Ratio
                </div>
                <div className="flex items-baseline gap-2 mt-1">
                  <span
                    className={`text-xl font-bold ${statusColors[fluxRatioStatus]}`}
                  >
                    {fluxRatio.toFixed(3)}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    (expected: 1.0)
                  </span>
                </div>
                {photometry.flux_ratio_error && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    ± {photometry.flux_ratio_error.toFixed(3)}
                  </div>
                )}
              </div>
            )}

            {/* Position Offset */}
            {photometry.position_offset_arcsec !== undefined && (
              <div
                className={`rounded-lg p-3 ${statusBgColors[positionStatus]}`}
              >
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Position Offset
                </div>
                <div className="flex items-baseline gap-2 mt-1">
                  <span
                    className={`text-xl font-bold ${statusColors[positionStatus]}`}
                  >
                    {photometry.position_offset_arcsec.toFixed(2)}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    arcsec
                  </span>
                </div>
                {photometry.peak_ra_deg !== undefined &&
                  photometry.peak_dec_deg !== undefined && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono">
                      RA: {photometry.peak_ra_deg.toFixed(5)}° Dec:{" "}
                      {photometry.peak_dec_deg.toFixed(5)}°
                    </div>
                  )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quality summary */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">
            Quality Assessment
          </span>
          <div className="flex items-center gap-2">
            {snrStatus !== "good" && (
              <span className={`${statusColors[snrStatus]}`}>
                {snrStatus === "critical" ? "⚠️ Low SNR" : "SNR marginal"}
              </span>
            )}
            {fluxRatio !== undefined && fluxRatioStatus !== "good" && (
              <span className={`${statusColors[fluxRatioStatus]}`}>
                {fluxRatioStatus === "critical"
                  ? "⚠️ Flux deviation"
                  : "Flux offset"}
              </span>
            )}
            {photometry.position_offset_arcsec !== undefined &&
              positionStatus !== "good" && (
                <span className={`${statusColors[positionStatus]}`}>
                  {positionStatus === "critical"
                    ? "⚠️ Position error"
                    : "Position offset"}
                </span>
              )}
            {snrStatus === "good" &&
              fluxRatioStatus === "good" &&
              positionStatus === "good" && (
                <span className="text-green-600 dark:text-green-400">
                  ✓ All metrics within tolerance
                </span>
              )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default PhotometryResultsPanel;
