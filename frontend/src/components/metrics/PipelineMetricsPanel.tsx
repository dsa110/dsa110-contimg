/**
 * Pipeline Metrics Panel Component
 *
 * Displays pipeline processing metrics (jobs, success rate, queue).
 */

import React from "react";
import type { PipelineMetrics, SystemMetric } from "../../types/prometheus";
import { MetricsTimeSeriesChart } from "./MetricsTimeSeriesChart";

interface PipelineMetricsPanelProps {
  /** Pipeline metrics data */
  metrics: PipelineMetrics;
  /** Optional history for time-series display */
  history?: {
    jobsPerHour: SystemMetric;
    successRate: SystemMetric;
    queueDepth: SystemMetric;
  };
  /** Show detailed charts */
  showCharts?: boolean;
  className?: string;
}

function getStatusFromValue(
  value: number,
  warningThreshold: number,
  criticalThreshold: number,
  higherIsWorse: boolean = true
): "healthy" | "warning" | "critical" {
  if (higherIsWorse) {
    if (value >= criticalThreshold) return "critical";
    if (value >= warningThreshold) return "warning";
    return "healthy";
  } else {
    if (value <= criticalThreshold) return "critical";
    if (value <= warningThreshold) return "warning";
    return "healthy";
  }
}

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  status: "healthy" | "warning" | "critical";
  icon: React.ReactNode;
}

function MetricCard({ label, value, subValue, status, icon }: MetricCardProps) {
  const statusColors = {
    healthy:
      "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30",
    warning:
      "text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/30",
    critical: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30",
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {label}
        </span>
        <div className={`p-1.5 rounded ${statusColors[status]}`}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        {value}
      </div>
      {subValue && (
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {subValue}
        </div>
      )}
    </div>
  );
}

export function PipelineMetricsPanel({
  metrics,
  history,
  showCharts = true,
  className = "",
}: PipelineMetricsPanelProps) {
  const jobsStatus = getStatusFromValue(metrics.jobs_per_hour, 5, 2, false);
  const successStatus = getStatusFromValue(
    metrics.success_rate_percent,
    95,
    90,
    false
  );
  const queueStatus = getStatusFromValue(metrics.queue_depth, 50, 100, true);
  const workerStatus = getStatusFromValue(
    (metrics.active_workers / metrics.total_workers) * 100,
    70,
    50,
    false
  );

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Pipeline Performance
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Job processing and queue metrics
        </p>
      </div>

      <div className="p-4">
        {/* Overview Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <MetricCard
            label="Jobs/Hour"
            value={metrics.jobs_per_hour.toFixed(1)}
            subValue={`Avg duration: ${metrics.avg_job_duration_sec.toFixed(
              0
            )}s`}
            status={jobsStatus}
            icon={
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            }
          />
          <MetricCard
            label="Success Rate"
            value={`${metrics.success_rate_percent.toFixed(1)}%`}
            status={successStatus}
            icon={
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            }
          />
          <MetricCard
            label="Queue Depth"
            value={metrics.queue_depth}
            status={queueStatus}
            icon={
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
            }
          />
          <MetricCard
            label="Active Workers"
            value={`${metrics.active_workers}/${metrics.total_workers}`}
            subValue={`${(
              (metrics.active_workers / metrics.total_workers) *
              100
            ).toFixed(0)}% capacity`}
            status={workerStatus}
            icon={
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
            }
          />
        </div>

        {/* Detailed Charts */}
        {showCharts && history && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricsTimeSeriesChart metric={history.jobsPerHour} height={100} />
            <MetricsTimeSeriesChart metric={history.successRate} height={100} />
            <MetricsTimeSeriesChart metric={history.queueDepth} height={100} />
          </div>
        )}
      </div>
    </div>
  );
}

export default PipelineMetricsPanel;
