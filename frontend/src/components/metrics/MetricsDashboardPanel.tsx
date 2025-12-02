/**
 * Metrics Dashboard Panel Component
 *
 * Main dashboard for displaying Prometheus metrics.
 * Combines resource and pipeline metrics in a unified view.
 */

import React, { useState } from "react";
import type { MetricsDashboard, SystemMetric } from "../../types/prometheus";
import { MetricsTimeSeriesChart } from "./MetricsTimeSeriesChart";
import { ResourceMetricsPanel } from "./ResourceMetricsPanel";
import { PipelineMetricsPanel } from "./PipelineMetricsPanel";

interface MetricsDashboardPanelProps {
  /** Dashboard metrics data */
  data: MetricsDashboard | undefined;
  /** Loading state */
  isLoading?: boolean;
  /** Error state */
  error?: Error | null;
  className?: string;
}

type TabId = "overview" | "resources" | "pipeline" | "custom";

interface Tab {
  id: TabId;
  label: string;
}

const tabs: Tab[] = [
  { id: "overview", label: "Overview" },
  { id: "resources", label: "Resources" },
  { id: "pipeline", label: "Pipeline" },
  { id: "custom", label: "Custom Metrics" },
];

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg"
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"
          />
        ))}
      </div>
    </div>
  );
}

function ErrorDisplay({ error }: { error: Error }) {
  return (
    <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4">
      <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
        <svg
          className="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <span className="font-medium">Failed to load metrics</span>
      </div>
      <p className="text-sm text-red-600 dark:text-red-400 mt-1">
        {error.message}
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-8">
      <svg
        className="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
      <p className="mt-2 text-gray-500 dark:text-gray-400">
        No metrics data available
      </p>
      <p className="text-sm text-gray-400 dark:text-gray-500">
        Prometheus may not be configured or reachable
      </p>
    </div>
  );
}

function OverviewTab({ data }: { data: MetricsDashboard }) {
  // Show key metrics in a compact overview
  const keyMetrics = data.metrics.slice(0, 6);

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">CPU</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {data.resources.cpu_percent.toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">Memory</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {data.resources.memory_percent.toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Jobs/Hour
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {data.pipeline.jobs_per_hour.toFixed(1)}
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Success Rate
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {data.pipeline.success_rate_percent.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Key Metrics Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {keyMetrics.map((metric) => (
          <MetricsTimeSeriesChart
            key={metric.id}
            metric={metric}
            height={100}
          />
        ))}
      </div>

      {/* Last Update */}
      <div className="text-xs text-gray-400 dark:text-gray-500 text-right">
        Last updated: {new Date(data.updated_at).toLocaleString()}
      </div>
    </div>
  );
}

function CustomMetricsTab({ metrics }: { metrics: SystemMetric[] }) {
  if (metrics.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        No custom metrics configured
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {metrics.map((metric) => (
        <MetricsTimeSeriesChart
          key={metric.id}
          metric={metric}
          height={120}
          showLegend
        />
      ))}
    </div>
  );
}

export function MetricsDashboardPanel({
  data,
  isLoading,
  error,
  className = "",
}: MetricsDashboardPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
      {/* Header with Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <div className="px-4 py-3 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Prometheus Metrics
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Real-time system and pipeline monitoring
            </p>
          </div>
          {data && (
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Live
              </span>
            </div>
          )}
        </div>

        <div className="px-4">
          <nav className="flex space-x-4" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {isLoading && <LoadingSkeleton />}
        {error && <ErrorDisplay error={error} />}
        {!isLoading && !error && !data && <EmptyState />}
        {!isLoading && !error && data && (
          <>
            {activeTab === "overview" && <OverviewTab data={data} />}
            {activeTab === "resources" && (
              <ResourceMetricsPanel
                metrics={{
                  cpu: data.metrics.find((m) => m.id === "cpu") || {
                    id: "cpu",
                    name: "CPU",
                    description: "CPU usage",
                    unit: "%",
                    current: data.resources.cpu_percent,
                    trend: "stable",
                    trendPercent: 0,
                    status: "healthy",
                    history: [],
                  },
                  memory: {
                    ...(data.metrics.find((m) => m.id === "memory") || {
                      id: "memory",
                      name: "Memory",
                      description: "Memory usage",
                      unit: "%",
                      current: data.resources.memory_percent,
                      trend: "stable",
                      trendPercent: 0,
                      status: "healthy",
                      history: [],
                    }),
                    total: 100,
                  },
                  diskIO: data.metrics.find((m) => m.id === "disk-io") || {
                    id: "disk-io",
                    name: "Disk I/O",
                    description: "Disk throughput",
                    unit: "bytes",
                    current: data.resources.disk_io_mbps * 1e6,
                    trend: "stable",
                    trendPercent: 0,
                    status: "healthy",
                    history: [],
                  },
                  network: data.metrics.find((m) => m.id === "network") || {
                    id: "network",
                    name: "Network I/O",
                    description: "Network throughput",
                    unit: "bytes",
                    current: data.resources.network_io_mbps * 1e6,
                    trend: "stable",
                    trendPercent: 0,
                    status: "healthy",
                    history: [],
                  },
                }}
                showCharts
              />
            )}
            {activeTab === "pipeline" && (
              <PipelineMetricsPanel
                metrics={data.pipeline}
                history={
                  data.metrics.some((m) => m.id === "jobs-per-hour")
                    ? {
                        jobsPerHour: data.metrics.find(
                          (m) => m.id === "jobs-per-hour"
                        )!,
                        successRate: data.metrics.find(
                          (m) => m.id === "success-rate"
                        )!,
                        queueDepth: data.metrics.find(
                          (m) => m.id === "queue-depth"
                        )!,
                      }
                    : undefined
                }
                showCharts
              />
            )}
            {activeTab === "custom" && (
              <CustomMetricsTab
                metrics={data.metrics.filter(
                  (m) =>
                    ![
                      "cpu",
                      "memory",
                      "disk-io",
                      "network",
                      "jobs-per-hour",
                      "success-rate",
                      "queue-depth",
                    ].includes(m.id)
                )}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default MetricsDashboardPanel;
