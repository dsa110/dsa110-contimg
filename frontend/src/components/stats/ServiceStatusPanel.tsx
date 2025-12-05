import { useState, useEffect, useCallback, useMemo } from "react";
import {
  ServiceHealthChecker,
  ServiceHealthResult,
  CheckDiagnostics,
  DEFAULT_SERVICES,
} from "../../utils/serviceHealthChecker";
import { logger } from "../../utils/logger";

/**
 * Internal service state for the panel
 */
interface ServiceStatus {
  name: string;
  port: number;
  description: string;
  status: "running" | "stopped" | "degraded" | "error" | "checking" | "unknown";
  responseTime?: number;
  lastChecked?: Date;
  error?: string;
  details?: Record<string, unknown>;
  /** Source of the health check result */
  source?: "backend-api" | "client-probe" | "cached" | "fallback";
  /** Consecutive failure count */
  failureCount?: number;
}

function StatusBadge({
  status,
  error,
}: {
  status: ServiceStatus["status"];
  error?: string;
}) {
  const styles: Record<ServiceStatus["status"], string> = {
    running:
      "bg-green-100 text-green-800 border-green-300 dark:bg-green-500/20 dark:text-green-400 dark:border-green-500/30",
    stopped:
      "bg-red-100 text-red-800 border-red-300 dark:bg-red-500/20 dark:text-red-400 dark:border-red-500/30",
    degraded:
      "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-500/20 dark:text-yellow-400 dark:border-yellow-500/30",
    error:
      "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-500/20 dark:text-orange-400 dark:border-orange-500/30",
    checking:
      "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-500/20 dark:text-blue-400 dark:border-blue-500/30 animate-pulse",
    unknown:
      "bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-500/20 dark:text-gray-400 dark:border-gray-500/30",
  };

  const labels: Record<ServiceStatus["status"], string> = {
    running: "● Running",
    stopped: "○ Stopped",
    degraded: "◐ Degraded",
    error: "⚠ Error",
    checking: "◌ Checking...",
    unknown: "? Unknown",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded border ${styles[status]}`}
      title={error || undefined}
    >
      {labels[status]}
    </span>
  );
}

/**
 * Badge showing the source of health check data
 */
function SourceBadge({ source }: { source?: ServiceStatus["source"] }) {
  if (!source) return null;

  const styles: Record<NonNullable<ServiceStatus["source"]>, string> = {
    "backend-api":
      "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400",
    "client-probe":
      "bg-purple-50 text-purple-600 dark:bg-purple-500/10 dark:text-purple-400",
    cached: "bg-gray-50 text-gray-500 dark:bg-gray-500/10 dark:text-gray-400",
    fallback:
      "bg-yellow-50 text-yellow-600 dark:bg-yellow-500/10 dark:text-yellow-400",
  };

  const labels: Record<NonNullable<ServiceStatus["source"]>, string> = {
    "backend-api": "API",
    "client-probe": "Direct",
    cached: "Cached",
    fallback: "Unknown",
  };

  return (
    <span className={`px-1.5 py-0.5 text-[10px] rounded ${styles[source]}`}>
      {labels[source]}
    </span>
  );
}

/**
 * Failure indicator badge
 */
function FailureBadge({ count }: { count?: number }) {
  if (!count || count === 0) return null;

  const severity =
    count >= 3
      ? "text-red-500"
      : count >= 2
      ? "text-orange-500"
      : "text-yellow-500";

  return (
    <span
      className={`text-[10px] ${severity}`}
      title={`${count} consecutive failure(s)`}
    >
      ×{count}
    </span>
  );
}

export interface ServiceStatusPanelProps {
  /** Show compact version (summary only) */
  compact?: boolean;
}

export function ServiceStatusPanel({
  compact = false,
}: ServiceStatusPanelProps = {}) {
  // Create health checker instance (memoized)
  const healthChecker = useMemo(() => new ServiceHealthChecker(), []);

  const [services, setServices] = useState<ServiceStatus[]>(
    DEFAULT_SERVICES.map((s) => ({
      name: s.name,
      port: s.port,
      description: s.description,
      status: "checking" as const,
    }))
  );
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [apiAvailable, setApiAvailable] = useState<boolean | null>(null);
  const [diagnostics, setDiagnostics] = useState<CheckDiagnostics | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      healthChecker.abort();
    };
  }, [healthChecker]);

  const checkAllServices = useCallback(async () => {
    setIsRefreshing(true);

    try {
      const result = await healthChecker.checkAllServices();

      // Transform results to internal state
      const updatedServices: ServiceStatus[] = result.results.map(
        (svc: ServiceHealthResult) => ({
          name: svc.name,
          port: svc.port,
          description: svc.description,
          status: svc.status,
          responseTime: svc.responseTime,
          lastChecked: svc.lastChecked,
          error: svc.error,
          details: svc.details,
          source: svc.source,
          failureCount: svc.failureCount,
        })
      );

      setServices(updatedServices);
      setLastRefresh(new Date());
      setApiAvailable(result.apiAvailable);
      setDiagnostics(result.diagnostics);
    } catch (err) {
      logger.error(
        "Health check failed",
        err instanceof Error ? err : { error: err }
      );
      // On complete failure, mark everything as unknown
      setServices((prev) =>
        prev.map((s) => ({
          ...s,
          status: "unknown" as const,
          error: "Health check failed",
          source: "fallback" as const,
        }))
      );
      setApiAvailable(false);
      setDiagnostics(null);
    }

    setIsRefreshing(false);
  }, [healthChecker]);

  useEffect(() => {
    checkAllServices();
    // Refresh every 30 seconds
    const interval = setInterval(checkAllServices, 30000);
    return () => clearInterval(interval);
  }, [checkAllServices]);

  const runningCount = services.filter((s) => s.status === "running").length;
  const stoppedCount = services.filter(
    (s) => s.status === "stopped" || s.status === "error"
  ).length;
  const totalCount = services.length;

  // Compact mode: show summary only
  if (compact) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  runningCount === totalCount
                    ? "bg-green-500"
                    : stoppedCount > 0
                    ? "bg-red-500"
                    : "bg-yellow-500"
                }`}
              />
              <span
                className="text-sm"
                style={{ color: "var(--color-text-primary)" }}
              >
                {runningCount}/{totalCount} services
              </span>
            </div>
            {stoppedCount > 0 && (
              <span className="text-xs text-red-600">{stoppedCount} down</span>
            )}
          </div>
          <button
            onClick={checkAllServices}
            disabled={isRefreshing}
            className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 disabled:opacity-50 rounded transition-colors"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {isRefreshing ? "..." : "Refresh"}
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {services.map((service) => (
            <div
              key={service.port}
              className="flex items-center gap-2 px-2 py-1.5 rounded text-xs"
              style={{ backgroundColor: "var(--color-bg-surface)" }}
              title={service.description}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  service.status === "running"
                    ? "bg-green-500"
                    : service.status === "checking"
                    ? "bg-blue-500 animate-pulse"
                    : service.status === "stopped" || service.status === "error"
                    ? "bg-red-500"
                    : "bg-yellow-500"
                }`}
              />
              <span
                className="truncate"
                style={{ color: "var(--color-text-primary)" }}
              >
                {service.name}
              </span>
              {service.responseTime !== undefined && (
                <span
                  className="text-[10px] ml-auto"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {service.responseTime.toFixed(0)}ms
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Full mode
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Service Status
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {runningCount}/{totalCount} services running
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 dark:text-gray-500">
            Last checked: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={checkAllServices}
            disabled={isRefreshing}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 
                       disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            {isRefreshing ? "Checking..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Diagnostics Banner */}
      {apiAvailable === false && (
        <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-500/10 border border-yellow-200 dark:border-yellow-500/30 rounded text-sm">
          <div className="flex items-start gap-2">
            <span className="text-yellow-600 dark:text-yellow-400 font-medium">
              ⚠ Backend API Unavailable
            </span>
          </div>
          <p className="mt-1 text-yellow-700 dark:text-yellow-300">
            Using client-side probes as fallback. Some services (e.g., Redis)
            cannot be checked directly from the browser.
          </p>
          {diagnostics && (
            <details className="mt-2">
              <summary className="cursor-pointer text-yellow-600 dark:text-yellow-400 text-xs">
                View diagnostics ({diagnostics.backendAttempts} backend attempt
                {diagnostics.backendAttempts !== 1 ? "s" : ""})
              </summary>
              <div className="mt-2 p-2 bg-yellow-100/50 dark:bg-yellow-900/20 rounded text-xs font-mono">
                {diagnostics.backendError && (
                  <p className="text-red-600 dark:text-red-400">
                    Error: {diagnostics.backendError}
                  </p>
                )}
                {diagnostics.individualProbes.length > 0 && (
                  <div className="mt-1">
                    <p className="text-yellow-800 dark:text-yellow-200">
                      Individual probe results:
                    </p>
                    <ul className="ml-2 mt-1 space-y-0.5">
                      {diagnostics.individualProbes.map((probe, i) => (
                        <li
                          key={i}
                          className={
                            probe.success
                              ? "text-green-600 dark:text-green-400"
                              : "text-red-600 dark:text-red-400"
                          }
                        >
                          {probe.service}: {probe.success ? "✓" : "✗"} (
                          {probe.source})
                          {probe.error && (
                            <span className="text-gray-500">
                              {" "}
                              - {probe.error}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      )}

      {/* API Available Indicator */}
      {apiAvailable === true && (
        <div className="mb-4 p-2 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded text-xs text-green-700 dark:text-green-400 flex items-center gap-2">
          <span>✓ Backend API connected</span>
          {diagnostics && diagnostics.backendAttempts > 1 && (
            <span className="text-green-600 dark:text-green-500">
              (recovered after {diagnostics.backendAttempts} attempt
              {diagnostics.backendAttempts !== 1 ? "s" : ""})
            </span>
          )}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              <th className="pb-2 font-medium">Service</th>
              <th className="pb-2 font-medium">Port</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Response</th>
              <th className="pb-2 font-medium hidden md:table-cell">Source</th>
              <th className="pb-2 font-medium hidden lg:table-cell">
                Description
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {services.map((service) => (
              <tr
                key={service.port}
                className="text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50"
              >
                <td className="py-3 font-medium text-gray-900 dark:text-white">
                  <div className="flex items-center gap-2">
                    {service.name}
                    <FailureBadge count={service.failureCount} />
                  </div>
                </td>
                <td className="py-3">
                  <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-blue-600 dark:text-blue-400 text-xs">
                    {service.port}
                  </code>
                </td>
                <td className="py-3">
                  <StatusBadge status={service.status} error={service.error} />
                </td>
                <td className="py-3 text-gray-500 dark:text-gray-400">
                  {service.responseTime !== undefined
                    ? `${service.responseTime.toFixed(0)}ms`
                    : "—"}
                </td>
                <td className="py-3 hidden md:table-cell">
                  <SourceBadge source={service.source} />
                </td>
                <td className="py-3 text-gray-400 dark:text-gray-500 text-xs hidden lg:table-cell">
                  {service.description}
                  {service.error && (
                    <span
                      className="ml-2 text-red-500 dark:text-red-400"
                      title={service.error}
                    >
                      ({service.error})
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Port Reservation Info */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <details className="text-sm">
          <summary className="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
            ℹ️ About Service Health Checks
          </summary>
          <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800/50 rounded text-gray-600 dark:text-gray-400 text-xs space-y-1">
            <p>
              Health checks are primarily performed <strong>server-side</strong>{" "}
              by the FastAPI backend, with client-side fallback probing when the
              backend is unavailable.
            </p>
            <p>
              <strong>Data sources:</strong>
            </p>
            <p>
              • <span className="text-blue-600 dark:text-blue-400">API</span> —
              Results from backend health checker (most reliable)
            </p>
            <p>
              •{" "}
              <span className="text-purple-600 dark:text-purple-400">
                Direct
              </span>{" "}
              — Client-side HTTP probe (may fail due to CORS)
            </p>
            <p>
              • <span className="text-gray-500">Cached</span> — Recent result
              from cache (5s TTL)
            </p>
            <p>
              •{" "}
              <span className="text-yellow-600 dark:text-yellow-400">
                Unknown
              </span>{" "}
              — Service cannot be probed (e.g., Redis)
            </p>
            <p className="mt-2">
              <strong>Resilience features:</strong>
            </p>
            <p>
              • Retry with exponential backoff (3 attempts, 500ms-5s delays)
            </p>
            <p>• Consecutive failure tracking (×N badge)</p>
            <p>• Auto-refresh every 30 seconds</p>
            <p>
              • Managed by systemd with auto-restart via{" "}
              <code className="text-blue-600 dark:text-blue-400">
                /usr/local/bin/claim-port.sh
              </code>
            </p>
          </div>
        </details>
      </div>
    </div>
  );
}

export default ServiceStatusPanel;
