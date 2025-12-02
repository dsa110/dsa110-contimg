/**
 * Resource Metrics Panel Component
 *
 * Displays system resource metrics (CPU, memory, disk I/O, network).
 */

import React from "react";
import type { ResourceMetrics } from "../../types/prometheus";
import { MetricsTimeSeriesChart } from "./MetricsTimeSeriesChart";

interface ResourceMetricsPanelProps {
  /** Resource metrics data */
  metrics: ResourceMetrics;
  /** Show detailed charts */
  showCharts?: boolean;
  className?: string;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1e12) return `${(bytes / 1e12).toFixed(1)} TB`;
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(1)} KB`;
  return `${bytes} B`;
}

function getStatusColor(status: "healthy" | "warning" | "critical"): string {
  switch (status) {
    case "healthy":
      return "text-green-600 dark:text-green-400";
    case "warning":
      return "text-yellow-600 dark:text-yellow-400";
    case "critical":
      return "text-red-600 dark:text-red-400";
  }
}

function getStatusBg(status: "healthy" | "warning" | "critical"): string {
  switch (status) {
    case "healthy":
      return "bg-green-500";
    case "warning":
      return "bg-yellow-500";
    case "critical":
      return "bg-red-500";
  }
}

interface ResourceGaugeProps {
  label: string;
  value: number;
  total?: number;
  unit: string;
  status: "healthy" | "warning" | "critical";
  percentUsed?: number;
}

function ResourceGauge({
  label,
  value,
  total,
  unit,
  status,
  percentUsed,
}: ResourceGaugeProps) {
  const percentage = percentUsed ?? (total ? (value / total) * 100 : value);

  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </span>
        <span className={`text-sm font-bold ${getStatusColor(status)}`}>
          {unit === "%" ? `${value.toFixed(1)}%` : formatBytes(value)}
          {total && ` / ${formatBytes(total)}`}
        </span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${getStatusBg(status)}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

export function ResourceMetricsPanel({
  metrics,
  showCharts = true,
  className = "",
}: ResourceMetricsPanelProps) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}
    >
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          System Resources
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Real-time system resource utilization
        </p>
      </div>

      <div className="p-4">
        {/* Overview Gauges */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <ResourceGauge
            label="CPU"
            value={metrics.cpu.current}
            unit="%"
            status={metrics.cpu.status}
          />
          <ResourceGauge
            label="Memory"
            value={metrics.memory.current}
            total={metrics.memory.total}
            unit="bytes"
            status={metrics.memory.status}
            percentUsed={(metrics.memory.current / metrics.memory.total) * 100}
          />
          <ResourceGauge
            label="Disk I/O"
            value={metrics.diskIO.current}
            unit="bytes"
            status={metrics.diskIO.status}
          />
          <ResourceGauge
            label="Network"
            value={metrics.network.current}
            unit="bytes"
            status={metrics.network.status}
          />
        </div>

        {/* Detailed Charts */}
        {showCharts && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MetricsTimeSeriesChart
              metric={{
                name: "CPU Usage",
                description: "Processor utilization over time",
                current: metrics.cpu.current,
                unit: "%",
                status: metrics.cpu.status,
                trend: metrics.cpu.trend,
                trendPercent: metrics.cpu.trendPercent,
                history: metrics.cpu.history,
              }}
              height={100}
            />
            <MetricsTimeSeriesChart
              metric={{
                name: "Memory Usage",
                description: "RAM utilization over time",
                current: (metrics.memory.current / metrics.memory.total) * 100,
                unit: "%",
                status: metrics.memory.status,
                trend: metrics.memory.trend,
                trendPercent: metrics.memory.trendPercent,
                history: metrics.memory.history.map((p) => ({
                  ...p,
                  value: (p.value / metrics.memory.total) * 100,
                })),
              }}
              height={100}
            />
            <MetricsTimeSeriesChart
              metric={{
                name: "Disk I/O",
                description: "Disk read/write throughput",
                current: metrics.diskIO.current,
                unit: "bytes",
                status: metrics.diskIO.status,
                trend: metrics.diskIO.trend,
                trendPercent: metrics.diskIO.trendPercent,
                history: metrics.diskIO.history,
              }}
              height={100}
            />
            <MetricsTimeSeriesChart
              metric={{
                name: "Network I/O",
                description: "Network bandwidth usage",
                current: metrics.network.current,
                unit: "bytes",
                status: metrics.network.status,
                trend: metrics.network.trend,
                trendPercent: metrics.network.trendPercent,
                history: metrics.network.history,
              }}
              height={100}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default ResourceMetricsPanel;
