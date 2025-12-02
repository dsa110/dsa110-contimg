/**
 * Storage Trend Chart Component
 *
 * Displays storage usage trends over time with growth projections.
 */

import React from "react";
import type { StorageTrend } from "../../types/storage";

interface StorageTrendChartProps {
  trends: StorageTrend[];
  className?: string;
}

function TrendLine({ trend }: { trend: StorageTrend }) {
  const { data_points, growth_rate_bytes_per_day, days_until_full } = trend;

  if (data_points.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 dark:text-gray-400">
        No trend data available
      </div>
    );
  }

  const minPercent = Math.min(...data_points.map((p) => p.usage_percent));
  const maxPercent = Math.max(...data_points.map((p) => p.usage_percent));
  const range = maxPercent - minPercent || 10;
  const padding = range * 0.1;

  const chartMin = Math.max(0, minPercent - padding);
  const chartMax = Math.min(100, maxPercent + padding);
  const chartRange = chartMax - chartMin;

  const width = 100;
  const height = 60;

  const points = data_points.map((p, i) => {
    const x = (i / (data_points.length - 1 || 1)) * width;
    const y = height - ((p.usage_percent - chartMin) / chartRange) * height;
    return { x, y, point: p };
  });

  const pathD = `M ${points.map((p) => `${p.x},${p.y}`).join(" L ")}`;

  // Format growth rate
  const formatGrowth = (bytesPerDay: number): string => {
    const absBytes = Math.abs(bytesPerDay);
    const sign = bytesPerDay >= 0 ? "+" : "-";
    if (absBytes >= 1e12)
      return `${sign}${(absBytes / 1e12).toFixed(2)} TB/day`;
    if (absBytes >= 1e9) return `${sign}${(absBytes / 1e9).toFixed(2)} GB/day`;
    if (absBytes >= 1e6) return `${sign}${(absBytes / 1e6).toFixed(2)} MB/day`;
    return `${sign}${(absBytes / 1e3).toFixed(2)} KB/day`;
  };

  const isGrowing = growth_rate_bytes_per_day > 0;
  const trendColor = isGrowing ? "text-orange-500" : "text-green-500";

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-gray-900 dark:text-gray-100">
          {trend.mount_point}
        </h4>
        <div className="flex items-center gap-3 text-sm">
          <span className={trendColor}>
            {formatGrowth(growth_rate_bytes_per_day)}
          </span>
          {days_until_full && days_until_full < 90 && (
            <span className="text-red-600 dark:text-red-400 font-medium">
              Full in ~{days_until_full} days
            </span>
          )}
        </div>
      </div>

      <div className="relative h-20 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full"
          preserveAspectRatio="none"
        >
          {/* Grid lines */}
          {[25, 50, 75].map((percent) => {
            if (percent < chartMin || percent > chartMax) return null;
            const y = height - ((percent - chartMin) / chartRange) * height;
            return (
              <line
                key={percent}
                x1="0"
                y1={y}
                x2={width}
                y2={y}
                stroke="currentColor"
                strokeDasharray="2,2"
                className="text-gray-300 dark:text-gray-600"
              />
            );
          })}

          {/* Trend line */}
          <path
            d={pathD}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={isGrowing ? "text-orange-500" : "text-green-500"}
          />

          {/* Data points */}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r="2"
              className={`${isGrowing ? "fill-orange-500" : "fill-green-500"}`}
            />
          ))}
        </svg>

        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-xs text-gray-500 dark:text-gray-400 -ml-8 w-8 text-right">
          <span>{chartMax.toFixed(0)}%</span>
          <span>{chartMin.toFixed(0)}%</span>
        </div>
      </div>

      {/* Time axis labels */}
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
        <span>{new Date(trend.period_start).toLocaleDateString()}</span>
        <span>{new Date(trend.period_end).toLocaleDateString()}</span>
      </div>
    </div>
  );
}

export function StorageTrendChart({
  trends,
  className = "",
}: StorageTrendChartProps) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Storage Trends
      </h3>

      <div className="space-y-6">
        {trends.map((trend) => (
          <TrendLine key={trend.mount_point} trend={trend} />
        ))}
      </div>

      {trends.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="text-4xl mb-2">📊</div>
          <div>No trend data available</div>
          <div className="text-sm">Check back after data collection starts</div>
        </div>
      )}
    </div>
  );
}

export default StorageTrendChart;
