/**
 * Calibrator Monitoring Panel Component
 *
 * Displays flux stability charts and calibrator health.
 */

import React, { useState } from "react";
import { useFluxMonitoring, useFluxHistory } from "../../api/health";
import type {
  FluxMonitoringStatus,
  FluxHistoryPoint,
} from "../../types/health";

interface CalibratorMonitoringPanelProps {
  className?: string;
}

function StatusIndicator({
  isStable,
  alertsCount,
}: {
  isStable: boolean;
  alertsCount: number;
}) {
  if (alertsCount > 0) {
    return (
      <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
        {alertsCount} alert{alertsCount > 1 ? "s" : ""}
      </span>
    );
  }
  if (isStable) {
    return (
      <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
        <span className="w-2 h-2 rounded-full bg-green-500" />
        Stable
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
      <span className="w-2 h-2 rounded-full bg-yellow-500" />
      Unstable
    </span>
  );
}

function FluxRatioChart({
  measurements,
}: {
  measurements: FluxHistoryPoint[];
}) {
  if (measurements.length === 0) {
    return (
      <div className="h-32 flex items-center justify-center text-gray-500 dark:text-gray-400">
        No measurements available
      </div>
    );
  }

  const minRatio = Math.min(...measurements.map((m) => m.flux_ratio));
  const maxRatio = Math.max(...measurements.map((m) => m.flux_ratio));
  const range = maxRatio - minRatio || 0.1;
  const padding = range * 0.1;

  const chartMin = minRatio - padding;
  const chartMax = maxRatio + padding;
  const chartRange = chartMax - chartMin;

  const width = 100;
  const height = 100;
  const points = measurements.map((m, i) => {
    const x = (i / (measurements.length - 1 || 1)) * width;
    const y = height - ((m.flux_ratio - chartMin) / chartRange) * height;
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(" L ")}`;

  // Reference line at 1.0
  const refY = height - ((1.0 - chartMin) / chartRange) * height;

  return (
    <div className="h-32 relative">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-full"
        preserveAspectRatio="none"
      >
        {/* Reference line at 1.0 */}
        {refY >= 0 && refY <= height && (
          <line
            x1="0"
            y1={refY}
            x2={width}
            y2={refY}
            stroke="currentColor"
            strokeDasharray="2,2"
            className="text-gray-400 dark:text-gray-500"
          />
        )}
        {/* Data line */}
        <path
          d={pathD}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-blue-500"
        />
        {/* Points */}
        {measurements.map((m, i) => {
          const x = (i / (measurements.length - 1 || 1)) * width;
          const y = height - ((m.flux_ratio - chartMin) / chartRange) * height;
          return (
            <circle key={i} cx={x} cy={y} r="2" className="fill-blue-500" />
          );
        })}
      </svg>
      {/* Y-axis labels */}
      <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-xs text-gray-500 dark:text-gray-400 -ml-8 w-8 text-right">
        <span>{chartMax.toFixed(2)}</span>
        <span>{chartMin.toFixed(2)}</span>
      </div>
    </div>
  );
}

function CalibratorCard({
  calibrator,
  isSelected,
  onClick,
}: {
  calibrator: FluxMonitoringStatus;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-colors ${
        isSelected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
          : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {calibrator.calibrator_name}
        </span>
        <StatusIndicator
          isStable={calibrator.is_stable}
          alertsCount={calibrator.alerts_count}
        />
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-400">
        <div>
          <span className="text-gray-500">Measurements:</span>{" "}
          {calibrator.n_measurements}
        </div>
        <div>
          <span className="text-gray-500">Mean ratio:</span>{" "}
          {calibrator.mean_flux_ratio?.toFixed(3) || "N/A"}
        </div>
        <div>
          <span className="text-gray-500">Std dev:</span>{" "}
          {calibrator.flux_ratio_std?.toFixed(3) || "N/A"}
        </div>
        <div>
          <span className="text-gray-500">Latest:</span>{" "}
          {calibrator.latest_flux_ratio?.toFixed(3) || "N/A"}
        </div>
      </div>
    </button>
  );
}

export function CalibratorMonitoringPanel({
  className = "",
}: CalibratorMonitoringPanelProps) {
  const { data: summary, isLoading, error } = useFluxMonitoring();
  const [selectedCalibrator, setSelectedCalibrator] = useState<string | null>(
    null
  );

  const { data: history } = useFluxHistory(
    selectedCalibrator || "",
    30,
    !!selectedCalibrator
  );

  if (isLoading) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-20 bg-gray-200 dark:bg-gray-700 rounded"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <div className="text-red-500">
          Failed to load calibrator monitoring data
        </div>
      </div>
    );
  }

  const calibrators = summary?.calibrators || [];

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Calibrator Flux Monitoring
        </h3>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {summary?.total_measurements || 0} total measurements
        </div>
      </div>

      {calibrators.length === 0 ? (
        <div className="text-gray-500 dark:text-gray-400 text-center py-8">
          No calibrator monitoring data available
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Calibrator list */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Calibrators ({calibrators.length})
            </h4>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {calibrators.map((cal) => (
                <CalibratorCard
                  key={cal.calibrator_name}
                  calibrator={cal}
                  isSelected={selectedCalibrator === cal.calibrator_name}
                  onClick={() => setSelectedCalibrator(cal.calibrator_name)}
                />
              ))}
            </div>
          </div>

          {/* Flux history chart */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Flux Ratio History
              {selectedCalibrator && (
                <span className="ml-2 text-blue-500">
                  ({selectedCalibrator})
                </span>
              )}
            </h4>
            {selectedCalibrator ? (
              history ? (
                <div>
                  <FluxRatioChart measurements={history.measurements} />
                  <div className="mt-2 grid grid-cols-4 gap-2 text-xs text-gray-600 dark:text-gray-400">
                    <div>
                      <span className="text-gray-500">Mean:</span>{" "}
                      {history.stats.mean_flux_ratio.toFixed(3)}
                    </div>
                    <div>
                      <span className="text-gray-500">Std:</span>{" "}
                      {history.stats.std_flux_ratio.toFixed(3)}
                    </div>
                    <div>
                      <span className="text-gray-500">Min:</span>{" "}
                      {history.stats.min_flux_ratio.toFixed(3)}
                    </div>
                    <div>
                      <span className="text-gray-500">Max:</span>{" "}
                      {history.stats.max_flux_ratio.toFixed(3)}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-32 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
                </div>
              )
            ) : (
              <div className="h-32 flex items-center justify-center text-gray-500 dark:text-gray-400">
                Select a calibrator to view history
              </div>
            )}
          </div>
        </div>
      )}

      {/* Alerts summary */}
      {summary && (summary.total_alerts ?? 0) > 0 && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span className="font-medium">
              {summary.total_alerts ?? 0} active alert
              {(summary.total_alerts ?? 0) > 1 ? "s" : ""}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default CalibratorMonitoringPanel;
