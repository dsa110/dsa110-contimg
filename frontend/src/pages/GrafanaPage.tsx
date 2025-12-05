/**
 * Grafana Dashboards Page
 *
 * Provides access to embedded Grafana dashboards for monitoring
 * pipeline performance, system resources, and operational metrics.
 */

import React, { useState } from "react";
import { Link } from "react-router-dom";
import { GrafanaEmbed, GrafanaPanel } from "../components/monitoring";
import { GRAFANA_CONFIG } from "../config";
import { ROUTES } from "../constants/routes";

/**
 * Time range options for dashboard selection
 */
const TIME_RANGES = [
  { label: "Last 15 min", value: "now-15m" },
  { label: "Last 1 hour", value: "now-1h" },
  { label: "Last 6 hours", value: "now-6h" },
  { label: "Last 24 hours", value: "now-24h" },
  { label: "Last 7 days", value: "now-7d" },
] as const;

/**
 * Dashboard definitions for the tab interface
 */
const DASHBOARDS = [
  {
    id: "pipeline-overview",
    label: "Pipeline Overview",
    description: "Conversion throughput, job queue, and processing metrics",
    uid: "pipeline-overview",
  },
  {
    id: "system-resources",
    label: "System Resources",
    description: "CPU, memory, disk, and network utilization",
    uid: "node-exporter",
  },
  {
    id: "api-performance",
    label: "API Performance",
    description: "Request latency, error rates, and endpoint metrics",
    uid: "fastapi-metrics",
  },
  {
    id: "streaming",
    label: "Streaming Converter",
    description: "Real-time ingest queue and processing status",
    uid: "streaming-converter",
  },
] as const;

/**
 * Quick stat panels for the overview section
 */
const QUICK_PANELS = [
  { uid: "pipeline-overview", panelId: 1, title: "Jobs/Hour" },
  { uid: "pipeline-overview", panelId: 2, title: "Queue Depth" },
  { uid: "node-exporter", panelId: 1, title: "CPU Usage" },
  { uid: "node-exporter", panelId: 2, title: "Memory Usage" },
] as const;

export function GrafanaPage() {
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [timeRange, setTimeRange] = useState("now-1h");

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <nav className="text-sm mb-1">
                <Link
                  to={ROUTES.HEALTH}
                  className="text-blue-600 hover:underline"
                >
                  Health Dashboard
                </Link>
                <span className="mx-2 text-gray-400">/</span>
                <span className="text-gray-600 dark:text-gray-400">
                  Grafana
                </span>
              </nav>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Grafana Dashboards
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Embedded monitoring dashboards for pipeline and system metrics
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Time range selector */}
              <div className="flex items-center gap-2">
                <label
                  htmlFor="time-range"
                  className="text-sm text-gray-600 dark:text-gray-400"
                >
                  Time Range:
                </label>
                <select
                  id="time-range"
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  {TIME_RANGES.map((range) => (
                    <option key={range.value} value={range.value}>
                      {range.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Open in Grafana button */}
              <a
                href={GRAFANA_CONFIG.baseUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M22.687 12.529c-.087-.527-.264-1.055-.527-1.406-.176-.264-.44-.44-.703-.527-.176-.088-.352-.088-.527-.088-.088 0-.176 0-.264.088-.088 0-.176.088-.264.088-.088.088-.176.088-.264.176-.088.088-.088.176-.176.264 0 .088-.088.176-.088.264 0 .088-.088.176-.088.264-.088.264-.264.527-.527.703-.264.176-.527.264-.879.264-.088 0-.176 0-.264-.088-.088 0-.176-.088-.264-.088-.088-.088-.176-.088-.264-.176-.088-.088-.088-.176-.176-.264 0-.088-.088-.176-.088-.264 0-.088-.088-.176-.088-.264-.088-.264-.176-.527-.352-.791-.176-.264-.44-.44-.703-.615-.264-.176-.527-.264-.879-.352-.352-.088-.703-.088-1.055-.088-.352 0-.703 0-1.055.088-.352.088-.615.176-.879.352-.264.176-.527.352-.703.615-.176.264-.264.527-.352.791 0 .088-.088.176-.088.264 0 .088-.088.176-.088.264 0 .088-.088.176-.176.264-.088.088-.176.176-.264.176-.088.088-.176.088-.264.088-.088.088-.176.088-.264.088-.352 0-.615-.088-.879-.264-.264-.176-.44-.44-.527-.703 0-.088-.088-.176-.088-.264 0-.088-.088-.176-.088-.264 0-.088-.088-.176-.176-.264-.088-.088-.176-.176-.264-.176-.088-.088-.176-.088-.264-.088-.088-.088-.176-.088-.264-.088-.176 0-.352 0-.527.088-.264.088-.527.264-.703.527-.264.352-.44.879-.527 1.406-.088.527-.088 1.143 0 1.758.088.615.264 1.23.527 1.758.264.527.615.967 1.055 1.318.44.352.967.615 1.582.791.615.176 1.318.264 2.109.176.791-.088 1.494-.264 2.109-.527.615-.264 1.143-.615 1.582-1.055.44-.44.791-.967 1.055-1.582.264-.615.44-1.318.527-2.109.088-.791.088-1.494 0-2.109z" />
                </svg>
                Open in Grafana
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
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Tab navigation */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-4 -mb-px" aria-label="Dashboard tabs">
            <button
              onClick={() => setActiveTab("overview")}
              className={`py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
                activeTab === "overview"
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              Quick Overview
            </button>
            {DASHBOARDS.map((dashboard) => (
              <button
                key={dashboard.id}
                onClick={() => setActiveTab(dashboard.id)}
                className={`py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
                  activeTab === dashboard.id
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                }`}
              >
                {dashboard.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {activeTab === "overview" ? (
          <>
            {/* Quick panels grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {QUICK_PANELS.map((panel, index) => (
                <div
                  key={index}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow p-2"
                >
                  <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 px-2">
                    {panel.title}
                  </h3>
                  <GrafanaPanel
                    dashboardUid={panel.uid}
                    panelId={panel.panelId}
                    height={120}
                    from={timeRange}
                    to="now"
                  />
                </div>
              ))}
            </div>

            {/* Dashboard cards */}
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Available Dashboards
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {DASHBOARDS.map((dashboard) => (
                <button
                  key={dashboard.id}
                  onClick={() => setActiveTab(dashboard.id)}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-left hover:shadow-lg transition-shadow group"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600">
                        {dashboard.label}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {dashboard.description}
                      </p>
                    </div>
                    <svg
                      className="w-5 h-5 text-gray-400 group-hover:text-blue-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          </>
        ) : (
          /* Full dashboard embed */
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            {DASHBOARDS.find((d) => d.id === activeTab) && (
              <>
                <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="font-medium text-gray-900 dark:text-gray-100">
                    {DASHBOARDS.find((d) => d.id === activeTab)?.label}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {DASHBOARDS.find((d) => d.id === activeTab)?.description}
                  </p>
                </div>
                <GrafanaEmbed
                  dashboardUid={
                    DASHBOARDS.find((d) => d.id === activeTab)?.uid || ""
                  }
                  height="calc(100vh - 280px)"
                  from={timeRange}
                  to="now"
                  kioskMode="tv"
                  refresh="30s"
                />
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default GrafanaPage;
