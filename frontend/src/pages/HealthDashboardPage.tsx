/**
 * Health Dashboard Page
 *
 * Unified health monitoring dashboard combining:
 * - System health overview
 * - Calibrator transit predictions
 * - Flux monitoring status
 * - Validity window timeline
 * - Active alerts
 * - Storage monitoring
 */

import React from "react";
import { Link } from "react-router-dom";
import { useSystemHealth, useAlerts } from "../api/health";
import type { ServiceStatusType } from "../types/health";
import {
  ValidityWindowTimeline,
  CalibratorMonitoringPanel,
  TransitWidget,
  AlertPolicyList,
} from "../components/health";
import { StorageMonitoringPanel } from "../components/storage";
import { MetricsDashboardPanel } from "../components/metrics";
import { useMetricsDashboard } from "../api/metrics";
import { ROUTES } from "../constants/routes";

// Map various status types to display status
function normalizeStatus(
  status: ServiceStatusType
): "healthy" | "degraded" | "unhealthy" | "unknown" {
  switch (status) {
    case "running":
    case "healthy":
      return "healthy";
    case "degraded":
      return "degraded";
    case "stopped":
    case "error":
    case "unhealthy":
      return "unhealthy";
    default:
      return "unknown";
  }
}

// Service status indicator
function ServiceStatus({
  name,
  status,
  lastCheck,
}: {
  name: string;
  status: ServiceStatusType;
  lastCheck?: string;
}) {
  const displayStatus = normalizeStatus(status);
  const statusColors = {
    healthy: "bg-green-500",
    degraded: "bg-yellow-500",
    unhealthy: "bg-red-500",
    unknown: "bg-gray-400",
  };

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      <div className="flex items-center gap-3">
        <span
          className={`w-3 h-3 rounded-full ${statusColors[displayStatus]}`}
        />
        <span className="font-medium text-gray-800 dark:text-gray-200">
          {name}
        </span>
      </div>
      {lastCheck && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {new Date(lastCheck).toLocaleTimeString()}
        </span>
      )}
      <Link
        to={{
          pathname: ROUTES.LOGS.LIST,
          search: new URLSearchParams({ service: name }).toString(),
        }}
        className="text-xs text-blue-600 hover:underline"
      >
        View logs
      </Link>
    </div>
  );
}

// System health overview panel
function SystemHealthPanel() {
  const { data, isLoading, error } = useSystemHealth();

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-12 bg-gray-200 dark:bg-gray-700 rounded"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div className="text-red-500">Failed to load system health</div>
      </div>
    );
  }

  if (!data) return null;

  const displayStatus = normalizeStatus(data.overall_status);
  const overallStatusColor = {
    healthy:
      "text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30",
    degraded:
      "text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30",
    unhealthy: "text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30",
    unknown: "text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-700",
  };

  const timestamp = data.timestamp || data.checked_at;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        System Health
      </h3>

      {/* Overall status banner */}
      <div
        className={`p-4 rounded-lg mb-4 ${overallStatusColor[displayStatus]}`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xl font-bold capitalize">{displayStatus}</span>
          {timestamp && (
            <span className="text-sm opacity-75">
              {new Date(timestamp).toLocaleString()}
            </span>
          )}
        </div>
      </div>

      {/* Services grid */}
      <div className="space-y-2">
        {data.services.map((service) => (
          <ServiceStatus
            key={service.name}
            name={service.name}
            status={service.status}
            lastCheck={service.last_check || service.checked_at}
          />
        ))}
      </div>

      {/* Summary stats */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {data.summary.healthy ?? data.summary.running ?? 0}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Healthy
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {data.summary.degraded ?? 0}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Degraded
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {data.summary.unhealthy ??
                data.summary.error ??
                data.summary.stopped ??
                0}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Unhealthy
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Active alerts panel
function AlertsPanel() {
  const { data, isLoading, error } = useAlerts({ acknowledged: false });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-16 bg-gray-200 dark:bg-gray-700 rounded"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div className="text-red-500">Failed to load alerts</div>
      </div>
    );
  }

  const activeAlerts = data?.alerts || [];
  const alertColors = {
    critical: "border-red-500 bg-red-50 dark:bg-red-900/20",
    warning: "border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20",
    info: "border-blue-500 bg-blue-50 dark:bg-blue-900/20",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Active Alerts
        </h3>
        <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
          {activeAlerts.length}
        </span>
      </div>

      {activeAlerts.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="text-4xl mb-2">✓</div>
          <div>No active alerts</div>
        </div>
      ) : (
        <div className="space-y-2">
          {activeAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-3 rounded-lg border-l-4 ${
                alertColors[alert.severity]
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">
                    {alert.message}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {alert.source || alert.alert_type} •{" "}
                    {new Date(
                      alert.created_at || alert.triggered_at
                    ).toLocaleString()}
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded uppercase ${
                    alert.severity === "critical"
                      ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                      : alert.severity === "warning"
                      ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                      : "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                  }`}
                >
                  {alert.severity}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function HealthDashboardPage() {
  const {
    data: metricsData,
    isLoading: metricsLoading,
    error: metricsError,
  } = useMetricsDashboard();

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Health Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Monitor system health, calibrator transits, storage, and validity
            windows
          </p>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Top row: System health + Alerts + Transits */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <SystemHealthPanel />
          <AlertsPanel />
          <TransitWidget />
        </div>

        {/* Alert policy management */}
        <div className="mb-6">
          <AlertPolicyList />
        </div>

        {/* Storage monitoring */}
        <div className="mb-6">
          <StorageMonitoringPanel showTrends={true} showCleanup={true} />
        </div>

        {/* Prometheus Metrics */}
        <div className="mb-6">
          <MetricsDashboardPanel
            data={metricsData}
            isLoading={metricsLoading}
            error={metricsError}
          />
        </div>

        {/* Calibrator monitoring */}
        <div className="mb-6">
          <CalibratorMonitoringPanel />
        </div>

        {/* Bottom row: Validity window timeline */}
        <div>
          <ValidityWindowTimeline hoursBack={24} hoursForward={48} />
        </div>
      </main>
    </div>
  );
}

export default HealthDashboardPage;
