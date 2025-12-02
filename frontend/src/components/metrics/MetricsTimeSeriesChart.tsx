/**
 * Metrics Time Series Chart Component
 *
 * Displays time-series metrics with interactive visualization.
 */

import React, { useMemo } from "react";
import type { SystemMetric } from "../../types/prometheus";

interface MetricsTimeSeriesChartProps {
  /** Metric data */
  metric: SystemMetric;
  /** Chart height */
  height?: number;
  /** Show legend */
  showLegend?: boolean;
  /** Time range in hours */
  timeRangeHours?: number;
  className?: string;
}

function formatValue(value: number, unit: string): string {
  if (unit === "bytes") {
    if (value >= 1e12) return `${(value / 1e12).toFixed(1)} TB`;
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)} GB`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)} MB`;
    return `${(value / 1e3).toFixed(1)} KB`;
  }
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "ms") return `${value.toFixed(0)} ms`;
  if (unit === "s") return `${value.toFixed(1)} s`;
  return value.toFixed(2);
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const statusColors = {
  healthy: "#22c55e", // green-500
  warning: "#eab308", // yellow-500
  critical: "#ef4444", // red-500
};

const statusBgColors = {
  healthy: "bg-green-100 dark:bg-green-900/30",
  warning: "bg-yellow-100 dark:bg-yellow-900/30",
  critical: "bg-red-100 dark:bg-red-900/30",
};

const trendIcons = {
  up: "↑",
  down: "↓",
  stable: "→",
};

export function MetricsTimeSeriesChart({
  metric,
  height = 120,
  showLegend = true,
  className = "",
}: MetricsTimeSeriesChartProps) {
  const { chartData, yMin, yMax } = useMemo(() => {
    if (metric.history.length === 0) {
      return { chartData: [], yMin: 0, yMax: 100 };
    }

    const values = metric.history.map((p) => p.value);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const range = maxVal - minVal || 10;
    const padding = range * 0.1;

    return {
      chartData: metric.history,
      yMin: Math.max(0, minVal - padding),
      yMax: maxVal + padding,
    };
  }, [metric.history]);

  const pathD = useMemo(() => {
    if (chartData.length < 2) return "";

    const width = 100;
    const yRange = yMax - yMin;

    const points = chartData.map((p, i) => {
      const x = (i / (chartData.length - 1)) * width;
      const y = height - ((p.value - yMin) / yRange) * height;
      return { x, y };
    });

    return `M ${points.map((p) => `${p.x},${p.y}`).join(" L ")}`;
  }, [chartData, yMin, yMax, height]);

  const areaD = useMemo(() => {
    if (chartData.length < 2) return "";

    const width = 100;
    const yRange = yMax - yMin;

    const points = chartData.map((p, i) => {
      const x = (i / (chartData.length - 1)) * width;
      const y = height - ((p.value - yMin) / yRange) * height;
      return { x, y };
    });

    return `M 0,${height} L ${points
      .map((p) => `${p.x},${p.y}`)
      .join(" L ")} L 100,${height} Z`;
  }, [chartData, yMin, yMax, height]);

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="font-medium text-gray-900 dark:text-gray-100">
            {metric.name}
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {metric.description}
          </p>
        </div>
        <div className="text-right">
          <div
            className={`text-2xl font-bold ${
              metric.status === "healthy"
                ? "text-gray-900 dark:text-gray-100"
                : metric.status === "warning"
                ? "text-yellow-600 dark:text-yellow-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {formatValue(metric.current, metric.unit)}
          </div>
          <div
            className={`text-xs flex items-center justify-end gap-1 ${
              metric.trend === "up"
                ? "text-red-500"
                : metric.trend === "down"
                ? "text-green-500"
                : "text-gray-500"
            }`}
          >
            <span>{trendIcons[metric.trend]}</span>
            <span>{metric.trendPercent.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="relative" style={{ height }}>
        {chartData.length > 1 ? (
          <svg
            viewBox={`0 0 100 ${height}`}
            className="w-full h-full"
            preserveAspectRatio="none"
          >
            {/* Area fill */}
            <path
              d={areaD}
              fill={statusColors[metric.status]}
              fillOpacity="0.1"
            />
            {/* Line */}
            <path
              d={pathD}
              fill="none"
              stroke={statusColors[metric.status]}
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            Insufficient data
          </div>
        )}

        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-xs text-gray-500 dark:text-gray-400 -ml-1 transform -translate-x-full pr-1">
          <span>{formatValue(yMax, metric.unit)}</span>
          <span>{formatValue(yMin, metric.unit)}</span>
        </div>
      </div>

      {/* Time axis */}
      {chartData.length > 1 && (
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>{formatTime(chartData[0].timestamp)}</span>
          <span>{formatTime(chartData[chartData.length - 1].timestamp)}</span>
        </div>
      )}

      {/* Status indicator */}
      {showLegend && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Status</span>
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                statusBgColors[metric.status]
              } ${
                metric.status === "healthy"
                  ? "text-green-700 dark:text-green-300"
                  : metric.status === "warning"
                  ? "text-yellow-700 dark:text-yellow-300"
                  : "text-red-700 dark:text-red-300"
              }`}
            >
              {metric.status}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default MetricsTimeSeriesChart;
