/**
 * Health Monitoring API Hooks
 *
 * React Query hooks for the health monitoring endpoints.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type {
  SystemHealthReport,
  ActiveValidityWindows,
  ValidityTimeline,
  FluxMonitoringSummary,
  FluxHistory,
  PointingStatus,
  AlertsResponse,
} from "../types/health";

const BASE_PATH = "/v1/health";

// =============================================================================
// Query Keys
// =============================================================================

export const healthKeys = {
  all: ["health"] as const,
  system: () => [...healthKeys.all, "system"] as const,
  validityWindows: (mjd?: number) =>
    [...healthKeys.all, "validity-windows", { mjd }] as const,
  validityTimeline: (hoursBack?: number, hoursForward?: number) =>
    [
      ...healthKeys.all,
      "validity-timeline",
      { hoursBack, hoursForward },
    ] as const,
  fluxMonitoring: () => [...healthKeys.all, "flux-monitoring"] as const,
  fluxHistory: (calibrator: string, days?: number) =>
    [...healthKeys.all, "flux-history", calibrator, { days }] as const,
  pointing: () => [...healthKeys.all, "pointing"] as const,
  alerts: (params?: AlertsQueryParams) =>
    [...healthKeys.all, "alerts", params] as const,
};

// =============================================================================
// API Types
// =============================================================================

interface AlertsQueryParams {
  severity?: string;
  acknowledged?: boolean;
  limit?: number;
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get system health report.
 */
export async function getSystemHealth(): Promise<SystemHealthReport> {
  const response = await apiClient.get<SystemHealthReport>(
    `${BASE_PATH}/system`
  );
  return response.data;
}

/**
 * Get active validity windows.
 */
export async function getValidityWindows(
  mjd?: number
): Promise<ActiveValidityWindows> {
  const params = mjd ? { mjd } : {};
  const response = await apiClient.get<ActiveValidityWindows>(
    `${BASE_PATH}/validity-windows`,
    { params }
  );
  return response.data;
}

/**
 * Get validity window timeline.
 */
export async function getValidityTimeline(
  hoursBack = 24,
  hoursForward = 48
): Promise<ValidityTimeline> {
  const response = await apiClient.get<ValidityTimeline>(
    `${BASE_PATH}/validity-windows/timeline`,
    { params: { hours_back: hoursBack, hours_forward: hoursForward } }
  );
  return response.data;
}

/**
 * Get flux monitoring summary.
 */
export async function getFluxMonitoring(): Promise<FluxMonitoringSummary> {
  const response = await apiClient.get<FluxMonitoringSummary>(
    `${BASE_PATH}/flux-monitoring`
  );
  return response.data;
}

/**
 * Get flux history for a calibrator.
 */
export async function getFluxHistory(
  calibrator: string,
  days = 30
): Promise<FluxHistory> {
  const response = await apiClient.get<FluxHistory>(
    `${BASE_PATH}/flux-monitoring/${encodeURIComponent(calibrator)}/history`,
    { params: { days } }
  );
  return response.data;
}

/**
 * Get current pointing status with transit predictions.
 */
export async function getPointingStatus(): Promise<PointingStatus> {
  const response = await apiClient.get<PointingStatus>(`${BASE_PATH}/pointing`);
  return response.data;
}

/**
 * Get monitoring alerts.
 */
export async function getAlerts(
  params?: AlertsQueryParams
): Promise<AlertsResponse> {
  const response = await apiClient.get<AlertsResponse>(`${BASE_PATH}/alerts`, {
    params,
  });
  return response.data;
}

/**
 * Acknowledge an alert.
 */
export async function acknowledgeAlert(alertId: number): Promise<void> {
  await apiClient.post(`${BASE_PATH}/alerts/${alertId}/acknowledge`);
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook to fetch system health with auto-refresh.
 */
export function useSystemHealth(refetchInterval = 30000) {
  return useQuery({
    queryKey: healthKeys.system(),
    queryFn: getSystemHealth,
    refetchInterval,
    staleTime: 15000,
  });
}

/**
 * Hook to fetch active validity windows.
 */
export function useValidityWindows(mjd?: number, refetchInterval = 60000) {
  return useQuery({
    queryKey: healthKeys.validityWindows(mjd),
    queryFn: () => getValidityWindows(mjd),
    refetchInterval,
    staleTime: 30000,
  });
}

/**
 * Hook to fetch validity window timeline.
 */
export function useValidityTimeline(
  hoursBack = 24,
  hoursForward = 48,
  refetchInterval = 60000
) {
  return useQuery({
    queryKey: healthKeys.validityTimeline(hoursBack, hoursForward),
    queryFn: () => getValidityTimeline(hoursBack, hoursForward),
    refetchInterval,
    staleTime: 30000,
  });
}

/**
 * Hook to fetch flux monitoring summary.
 */
export function useFluxMonitoring(refetchInterval = 60000) {
  return useQuery({
    queryKey: healthKeys.fluxMonitoring(),
    queryFn: getFluxMonitoring,
    refetchInterval,
    staleTime: 30000,
  });
}

/**
 * Hook to fetch flux history for a calibrator.
 */
export function useFluxHistory(calibrator: string, days = 30, enabled = true) {
  return useQuery({
    queryKey: healthKeys.fluxHistory(calibrator, days),
    queryFn: () => getFluxHistory(calibrator, days),
    enabled: enabled && !!calibrator,
    staleTime: 60000,
  });
}

/**
 * Hook to fetch current pointing status.
 */
export function usePointingStatus(refetchInterval = 15000) {
  return useQuery({
    queryKey: healthKeys.pointing(),
    queryFn: getPointingStatus,
    refetchInterval,
    staleTime: 10000,
  });
}

/**
 * Hook to fetch monitoring alerts.
 *
 * @param params - Optional query parameters
 *   - severity: Filter by severity (info, warning, critical)
 *   - acknowledged: Filter by acknowledgement status (true/false)
 *   - limit: Max number of alerts to return
 * @param refetchInterval - Auto-refresh interval in ms (default 30s)
 */
export function useAlerts(params?: AlertsQueryParams, refetchInterval = 30000) {
  return useQuery({
    queryKey: healthKeys.alerts(params),
    queryFn: () => getAlerts(params),
    refetchInterval,
    staleTime: 15000,
  });
}

/**
 * Hook to acknowledge an alert.
 */
export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: healthKeys.all });
    },
  });
}
