/**
 * Prometheus Metrics API Hooks
 *
 * React Query hooks for fetching Prometheus metrics data.
 */

import { useQuery } from "@tanstack/react-query";
import apiClient from "./client";
import type {
  MetricsDashboard,
  PrometheusQueryResult,
  SystemMetric,
} from "../types/prometheus";

const BASE_PATH = "/v1/metrics";

// =============================================================================
// Query Keys
// =============================================================================

export const metricsKeys = {
  all: ["metrics"] as const,
  dashboard: () => [...metricsKeys.all, "dashboard"] as const,
  query: (query: string, start?: number, end?: number, step?: number) =>
    [...metricsKeys.all, "query", { query, start, end, step }] as const,
  metric: (metricId: string, hours?: number) =>
    [...metricsKeys.all, "metric", metricId, { hours }] as const,
};

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get the metrics dashboard summary.
 */
export async function getMetricsDashboard(): Promise<MetricsDashboard> {
  const response = await apiClient.get<MetricsDashboard>(
    `${BASE_PATH}/dashboard`
  );
  return response.data;
}

/**
 * Execute a Prometheus query.
 */
export async function queryPrometheus(
  query: string,
  start?: number,
  end?: number,
  step?: number
): Promise<PrometheusQueryResult> {
  const params: Record<string, string | number> = { query };
  if (start) params.start = start;
  if (end) params.end = end;
  if (step) params.step = step;

  const response = await apiClient.get<PrometheusQueryResult>(
    `${BASE_PATH}/query`,
    { params }
  );
  return response.data;
}

/**
 * Get a specific metric's history.
 */
export async function getMetricHistory(
  metricId: string,
  hours = 24
): Promise<SystemMetric> {
  const response = await apiClient.get<SystemMetric>(
    `${BASE_PATH}/${metricId}/history`,
    { params: { hours } }
  );
  return response.data;
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook to fetch the metrics dashboard with auto-refresh.
 */
export function useMetricsDashboard(refetchInterval = 15000) {
  return useQuery({
    queryKey: metricsKeys.dashboard(),
    queryFn: getMetricsDashboard,
    refetchInterval,
    staleTime: 10000,
  });
}

/**
 * Hook to execute a Prometheus query.
 */
export function usePrometheusQuery(
  query: string,
  options?: {
    start?: number;
    end?: number;
    step?: number;
    enabled?: boolean;
    refetchInterval?: number;
  }
) {
  const { start, end, step, enabled = true, refetchInterval } = options || {};

  return useQuery({
    queryKey: metricsKeys.query(query, start, end, step),
    queryFn: () => queryPrometheus(query, start, end, step),
    enabled: enabled && !!query,
    refetchInterval,
    staleTime: 10000,
  });
}

/**
 * Hook to fetch a specific metric's history.
 */
export function useMetricHistory(metricId: string, hours = 24, enabled = true) {
  return useQuery({
    queryKey: metricsKeys.metric(metricId, hours),
    queryFn: () => getMetricHistory(metricId, hours),
    enabled: enabled && !!metricId,
    staleTime: 30000,
  });
}
