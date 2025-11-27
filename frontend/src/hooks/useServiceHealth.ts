/**
 * useServiceHealth - Check service availability before rendering
 *
 * Provides graceful degradation by checking if backend services
 * are available before attempting to render dependent components.
 */
import { useQuery, useQueries } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { FeatureFlags } from "../config/features";
import { getFeatureHealthEndpoint, isFeatureEnabled } from "../config/features";

export type ServiceStatus = "healthy" | "degraded" | "down" | "unknown" | "disabled";

export interface ServiceHealth {
  status: ServiceStatus;
  lastChecked: Date | null;
  error?: string;
  responseTime?: number;
}

export type ServiceHealthMap = Record<string, ServiceHealth>;

/**
 * Check a single service's health
 */
async function checkServiceHealth(endpoint: string): Promise<ServiceHealth> {
  const startTime = Date.now();
  try {
    await apiClient.get(endpoint, {
      timeout: 5000, // 5 second timeout for health checks
    });

    const responseTime = Date.now() - startTime;

    // Consider slow responses as degraded
    const status: ServiceStatus = responseTime > 3000 ? "degraded" : "healthy";

    return {
      status,
      lastChecked: new Date(),
      responseTime,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    // Check if it's a 404 (endpoint doesn't exist) vs actual failure
    const axiosError = error as { response?: { status: number } };
    if (axiosError.response?.status === 404) {
      return {
        status: "unknown",
        lastChecked: new Date(),
        error: "Service endpoint not found",
      };
    }

    return {
      status: "down",
      lastChecked: new Date(),
      error: errorMessage,
    };
  }
}

/**
 * Hook to check health of a single service
 *
 * @param serviceName - Feature name to check
 * @param options - Query options
 */
export function useServiceHealth(
  serviceName: keyof FeatureFlags,
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
) {
  const endpoint = getFeatureHealthEndpoint(serviceName);
  const featureEnabled = isFeatureEnabled(serviceName);

  return useQuery({
    queryKey: ["service-health", serviceName],
    queryFn: async (): Promise<ServiceHealth> => {
      if (!featureEnabled) {
        return {
          status: "disabled",
          lastChecked: new Date(),
          error: "Feature is disabled",
        };
      }

      if (!endpoint) {
        return {
          status: "unknown",
          lastChecked: new Date(),
          error: "No health endpoint configured",
        };
      }

      return checkServiceHealth(endpoint);
    },
    // Default: check every 30 seconds
    refetchInterval: options?.refetchInterval ?? 30000,
    // Only run if enabled (default true)
    enabled: options?.enabled ?? true,
    // Keep stale data while refetching
    staleTime: 10000,
    // Don't retry health checks aggressively
    retry: 1,
    retryDelay: 1000,
  });
}

/**
 * Hook to check health of multiple services at once
 *
 * @param serviceNames - Array of feature names to check
 * @returns Object mapping service names to their health status
 *
 * @example
 * const health = useMultiServiceHealth(['absurd', 'carta', 'events']);
 * if (health.absurd?.status === 'down') {
 *   return <ServiceUnavailable service="absurd" />;
 * }
 */
export function useMultiServiceHealth(
  serviceNames: (keyof FeatureFlags)[],
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
): ServiceHealthMap {
  const queries = useQueries({
    queries: serviceNames.map((serviceName) => {
      const endpoint = getFeatureHealthEndpoint(serviceName);
      const featureEnabled = isFeatureEnabled(serviceName);

      return {
        queryKey: ["service-health", serviceName],
        queryFn: async (): Promise<ServiceHealth> => {
          if (!featureEnabled) {
            return {
              status: "disabled" as ServiceStatus,
              lastChecked: new Date(),
              error: "Feature is disabled",
            };
          }

          if (!endpoint) {
            return {
              status: "unknown" as ServiceStatus,
              lastChecked: new Date(),
              error: "No health endpoint configured",
            };
          }

          return checkServiceHealth(endpoint);
        },
        refetchInterval: options?.refetchInterval ?? 30000,
        enabled: options?.enabled ?? true,
        staleTime: 10000,
        retry: 1,
      };
    }),
  });

  // Build the result map
  const result: ServiceHealthMap = {};
  serviceNames.forEach((name, index) => {
    const query = queries[index];
    if (query.data) {
      result[name] = query.data;
    } else {
      result[name] = {
        status: query.isLoading ? "unknown" : "down",
        lastChecked: new Date(),
        error: query.error instanceof Error ? query.error.message : "Unknown error",
      };
    }
  });

  return result;
}

/**
 * Hook to get overall system health summary
 */
export function useSystemHealthSummary() {
  const services: (keyof FeatureFlags)[] = ["absurd", "carta", "events", "cache", "dlq"];
  const health = useMultiServiceHealth(services);

  const summary = {
    healthy: 0,
    degraded: 0,
    down: 0,
    disabled: 0,
    unknown: 0,
  };

  for (const service of services) {
    const status = health[service].status;
    summary[status]++;
  }

  const overallStatus: ServiceStatus =
    summary.down > 0
      ? "down"
      : summary.degraded > 0
        ? "degraded"
        : summary.healthy > 0
          ? "healthy"
          : "unknown";

  return {
    services: health,
    summary,
    overallStatus,
  };
}
