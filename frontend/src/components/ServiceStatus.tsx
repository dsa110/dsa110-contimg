/**
 * Service Status Component
 *
 * Displays real-time health status of backend services with robust error handling,
 * retry logic, and state preservation on errors.
 */
import { useState, useEffect, useCallback } from "react";
import { logger } from "../utils/logger";
import "./ServiceStatus.css";

interface ServiceInfo {
  status: "healthy" | "unhealthy" | "degraded" | "unknown";
  error?: string;
  last_check?: string;
}

interface ServicesResponse {
  [serviceName: string]: ServiceInfo;
}

interface ServicesState {
  services: ServicesResponse | null;
  lastUpdated: number | null;
  error: string | null;
  isStale: boolean;
}

const STALE_THRESHOLD_MS = 60000; // 60 seconds
const MAX_RETRY_DELAY_MS = 30000; // 30 seconds

const ServiceStatus = () => {
  const [state, setState] = useState<ServicesState>({
    services: null,
    lastUpdated: null,
    error: null,
    isStale: false,
  });
  const [loading, setLoading] = useState(true);
  const [retryCount, setRetryCount] = useState(0);

  /**
   * Calculate exponential backoff delay
   */
  const getRetryDelay = useCallback((attempt: number): number => {
    const delay = Math.min(1000 * Math.pow(2, attempt), MAX_RETRY_DELAY_MS);
    return delay;
  }, []);

  /**
   * Check if data is stale
   */
  const checkStaleData = useCallback(() => {
    setState((prev) => {
      if (!prev.lastUpdated) return prev;

      const isStale = Date.now() - prev.lastUpdated > STALE_THRESHOLD_MS;
      if (isStale !== prev.isStale) {
        return { ...prev, isStale };
      }
      return prev;
    });
  }, []);

  /**
   * Check services health
   */
  const checkServices = useCallback(async () => {
    try {
      const response = await fetch("/api/health/services");

      // Validate response status before parsing
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: ServicesResponse = await response.json();

      // Validate response structure
      if (!data || typeof data !== "object") {
        throw new Error("Invalid response format from services endpoint");
      }

      // Success - update state and reset retry count
      setState({
        services: data,
        lastUpdated: Date.now(),
        error: null,
        isStale: false,
      });
      setRetryCount(0);

      logger.debug("Services status updated", {
        serviceCount: Object.keys(data).length,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error("Failed to check services:", {
        error: errorMessage,
        retryCount,
      });

      // Preserve previous services data but indicate error
      setState((prev) => ({
        ...prev, // Keep previous services data
        error: errorMessage,
        isStale: true,
      }));

      // Increment retry count for exponential backoff
      setRetryCount((prev) => prev + 1);
    } finally {
      setLoading(false);
    }
  }, [retryCount]);

  // Initial load and periodic refresh
  useEffect(() => {
    checkServices();

    // Set up periodic check with exponential backoff on errors
    const delay = retryCount > 0 ? getRetryDelay(retryCount) : 30000;
    const interval = setInterval(checkServices, delay);

    return () => clearInterval(interval);
  }, [checkServices, retryCount, getRetryDelay]);

  // Check for stale data every 10 seconds
  useEffect(() => {
    const staleCheckInterval = setInterval(checkStaleData, 10000);
    return () => clearInterval(staleCheckInterval);
  }, [checkStaleData]);

  // Don't render anything during initial load
  if (loading && !state.services) {
    return null;
  }

  // Don't render if no services data available
  if (!state.services) {
    return null;
  }

  return (
    <div className="service-status">
      {state.error && (
        <div className="service-indicator error" title={`Error: ${state.error}`}>
          <span className="service-name">Services</span>
          <span className="status-dot unknown"></span>
          <span className="service-error" title={state.error}>
            ⚠
          </span>
        </div>
      )}
      {state.isStale && !state.error && (
        <div className="service-indicator warning" title="Service data may be stale">
          <span className="service-name">Status</span>
          <span className="status-dot degraded"></span>
          <span className="service-error" title="Data may be stale">
            ⏱
          </span>
        </div>
      )}
      {Object.entries(state.services).map(([name, service]) => (
        <div key={name} className={`service-indicator ${service.status}`}>
          <span className="service-name">{name}</span>
          <span className={`status-dot ${service.status}`}></span>
          {service.error && (
            <span className="service-error" title={service.error}>
              ⚠
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

export default ServiceStatus;
