import { useState, useEffect, useCallback } from "react";

/**
 * Service status as returned by the backend API.
 */
interface ServiceStatusResponse {
  name: string;
  port: number;
  description: string;
  status: "running" | "stopped" | "degraded" | "error" | "checking";
  responseTime: number;
  lastChecked: string;
  error: string | null;
  details: Record<string, unknown> | null;
}

/**
 * Full response from /api/services/status endpoint.
 */
interface ServicesStatusResponse {
  services: ServiceStatusResponse[];
  summary: {
    total: number;
    running: number;
    stopped: number;
  };
  timestamp: string;
}

/**
 * Internal service state with parsed dates.
 */
interface ServiceStatus {
  name: string;
  port: number;
  description: string;
  status: "running" | "stopped" | "degraded" | "error" | "checking";
  responseTime?: number;
  lastChecked?: Date;
  error?: string;
  details?: Record<string, unknown>;
}

// Fallback service definitions for initial state
const SERVICES_FALLBACK: Omit<ServiceStatus, "status" | "responseTime" | "lastChecked">[] = [
  { name: "Vite Dev Server", port: 3000, description: "Frontend development server with HMR" },
  { name: "Grafana", port: 3030, description: "Metrics visualization dashboards" },
  { name: "Redis", port: 6379, description: "API response caching" },
  { name: "FastAPI Backend", port: 8000, description: "REST API for pipeline data" },
  { name: "MkDocs", port: 8001, description: "Documentation server (dev only)" },
  { name: "Prometheus", port: 9090, description: "Metrics collection and storage" },
];

/**
 * Fetch service status from the backend API.
 * The backend performs server-side health checks, bypassing browser CORS/CSP restrictions.
 */
async function fetchServicesStatus(): Promise<ServicesStatusResponse | null> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const response = await fetch("/api/services/status", {
      method: "GET",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
      },
    });
    clearTimeout(timeout);

    if (!response.ok) {
      console.warn(`Services status API returned ${response.status}`);
      return null;
    }

    return await response.json();
  } catch (err) {
    console.warn("Failed to fetch services status:", err);
    return null;
  }
}

function StatusBadge({ status, error }: { status: ServiceStatus["status"]; error?: string }) {
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
  };

  const labels: Record<ServiceStatus["status"], string> = {
    running: "● Running",
    stopped: "○ Stopped",
    degraded: "◐ Degraded",
    error: "⚠ Error",
    checking: "◌ Checking...",
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

export function ServiceStatusPanel() {
  const [services, setServices] = useState<ServiceStatus[]>(
    SERVICES_FALLBACK.map((s) => ({ ...s, status: "checking" as const }))
  );
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const checkAllServices = useCallback(async () => {
    setIsRefreshing(true);
    setApiError(null);

    const result = await fetchServicesStatus();

    if (result) {
      // Transform API response to internal state
      const updatedServices: ServiceStatus[] = result.services.map((svc) => ({
        name: svc.name,
        port: svc.port,
        description: svc.description,
        status: svc.status,
        responseTime: svc.responseTime,
        lastChecked: new Date(svc.lastChecked),
        error: svc.error || undefined,
        details: svc.details || undefined,
      }));
      setServices(updatedServices);
      setLastRefresh(new Date(result.timestamp));
    } else {
      // API failed - mark all services as unknown/error
      setApiError("Could not reach the backend API. Status unknown.");
      setServices((prev) =>
        prev.map((s) => ({
          ...s,
          status: s.port === 8000 ? ("stopped" as const) : ("error" as const),
          error: "Backend API unavailable",
        }))
      );
      setLastRefresh(new Date());
    }

    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    checkAllServices();
    // Refresh every 30 seconds
    const interval = setInterval(checkAllServices, 30000);
    return () => clearInterval(interval);
  }, [checkAllServices]);

  const runningCount = services.filter((s) => s.status === "running").length;
  const totalCount = services.length;

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Service Status</h2>
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

      {/* API Error Banner */}
      {apiError && (
        <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-500/10 border border-yellow-200 dark:border-yellow-500/30 rounded text-yellow-800 dark:text-yellow-400 text-sm">
          <strong>⚠ Warning:</strong> {apiError}
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
              <th className="pb-2 font-medium hidden md:table-cell">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {services.map((service) => (
              <tr
                key={service.port}
                className="text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50"
              >
                <td className="py-3 font-medium text-gray-900 dark:text-white">{service.name}</td>
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
                <td className="py-3 text-gray-400 dark:text-gray-500 text-xs hidden md:table-cell">
                  {service.description}
                  {service.error && (
                    <span className="ml-2 text-red-500 dark:text-red-400" title={service.error}>
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
              Health checks are performed <strong>server-side</strong> by the FastAPI backend,
              ensuring accurate results regardless of browser security restrictions.
            </p>
            <p>• HTTP services checked via their health endpoints</p>
            <p>• Redis checked using native PING/PONG protocol</p>
            <p>• Status refreshes automatically every 30 seconds</p>
            <p>
              • Managed by systemd with auto-restart via{" "}
              <code className="text-blue-600 dark:text-blue-400">/usr/local/bin/claim-port.sh</code>
            </p>
          </div>
        </details>
      </div>
    </div>
  );
}

export default ServiceStatusPanel;
