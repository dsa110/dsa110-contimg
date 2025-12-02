/**
 * Antenna Flagging Summary Component
 *
 * Displays per-antenna flagging status with visual heatmap.
 */

import React from "react";

interface AntennaFlaggingSummaryProps {
  /** Per-antenna flagging percentages */
  antennaFlagging: Record<string, number>;
  /** Maximum acceptable flagging percentage */
  maxThreshold?: number;
  /** Warning threshold percentage */
  warningThreshold?: number;
  className?: string;
}

function getFlaggingColor(
  percent: number,
  warning: number,
  critical: number
): string {
  if (percent >= critical) return "bg-red-500";
  if (percent >= warning) return "bg-yellow-500";
  if (percent >= warning * 0.5) return "bg-orange-400";
  if (percent > 0) return "bg-green-400";
  return "bg-green-500";
}

function getTextColor(
  percent: number,
  warning: number,
  critical: number
): string {
  if (percent >= critical) return "text-red-600 dark:text-red-400";
  if (percent >= warning) return "text-yellow-600 dark:text-yellow-400";
  return "text-gray-600 dark:text-gray-400";
}

export function AntennaFlaggingSummary({
  antennaFlagging,
  maxThreshold = 50,
  warningThreshold = 20,
  className = "",
}: AntennaFlaggingSummaryProps) {
  const antennas = Object.entries(antennaFlagging).sort((a, b) => {
    // Sort by antenna number
    const numA = parseInt(a[0].replace(/\D/g, ""), 10) || 0;
    const numB = parseInt(b[0].replace(/\D/g, ""), 10) || 0;
    return numA - numB;
  });

  const avgFlagging =
    antennas.length > 0
      ? antennas.reduce((sum, [, pct]) => sum + pct, 0) / antennas.length
      : 0;

  const flaggedAntennas = antennas.filter(([, pct]) => pct >= warningThreshold);
  const severelyFlagged = antennas.filter(([, pct]) => pct >= maxThreshold);

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Antenna Flagging
        </h3>
        <div className="text-right text-sm">
          <div className="text-gray-600 dark:text-gray-400">
            Avg: <span className="font-mono">{avgFlagging.toFixed(1)}%</span>
          </div>
          {severelyFlagged.length > 0 && (
            <div className="text-red-600 dark:text-red-400">
              {severelyFlagged.length} antenna(s) &gt;{maxThreshold}%
            </div>
          )}
        </div>
      </div>

      {/* Antenna grid */}
      <div className="grid grid-cols-8 sm:grid-cols-10 md:grid-cols-12 gap-1">
        {antennas.map(([antenna, percent]) => (
          <div
            key={antenna}
            className="relative group"
            title={`${antenna}: ${percent.toFixed(1)}% flagged`}
          >
            <div
              className={`aspect-square rounded flex items-center justify-center text-xs font-medium text-white ${getFlaggingColor(
                percent,
                warningThreshold,
                maxThreshold
              )}`}
            >
              {antenna.replace(/^ant?/i, "")}
            </div>
            {/* Tooltip */}
            <div className="absolute z-10 bottom-full left-1/2 transform -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
              {antenna}: {percent.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-green-500" />
          <span className="text-gray-600 dark:text-gray-400">
            &lt;{warningThreshold * 0.5}%
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-yellow-500" />
          <span className="text-gray-600 dark:text-gray-400">
            {warningThreshold}-{maxThreshold}%
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-500" />
          <span className="text-gray-600 dark:text-gray-400">
            &gt;{maxThreshold}%
          </span>
        </div>
      </div>

      {/* Flagged antenna details */}
      {flaggedAntennas.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
            Flagged Antennas
          </h4>
          <div className="flex flex-wrap gap-2">
            {flaggedAntennas.map(([antenna, percent]) => (
              <span
                key={antenna}
                className={`px-2 py-1 rounded text-xs font-medium ${
                  percent >= maxThreshold
                    ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                    : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                }`}
              >
                {antenna}: {percent.toFixed(1)}%
              </span>
            ))}
          </div>
        </div>
      )}

      {antennas.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No antenna flagging data available
        </div>
      )}
    </div>
  );
}

export default AntennaFlaggingSummary;
