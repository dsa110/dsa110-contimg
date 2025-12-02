/**
 * Storage Monitoring API Hooks
 *
 * React Query hooks for storage and disk usage monitoring endpoints.
 */

import { useQuery } from "@tanstack/react-query";
import apiClient from "./client";
import type {
  StorageSummary,
  CleanupRecommendations,
  StorageTrend,
} from "../types/storage";

const BASE_PATH = "/api/v1/health/storage";

// =============================================================================
// Query Keys
// =============================================================================

export const storageKeys = {
  all: ["storage"] as const,
  summary: () => [...storageKeys.all, "summary"] as const,
  cleanup: () => [...storageKeys.all, "cleanup"] as const,
  trends: (days?: number) => [...storageKeys.all, "trends", { days }] as const,
};

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get storage summary with disk usage and directory breakdown.
 */
export async function getStorageSummary(): Promise<StorageSummary> {
  const response = await apiClient.get<StorageSummary>(`${BASE_PATH}/summary`);
  return response.data;
}

/**
 * Get cleanup recommendations.
 */
export async function getCleanupRecommendations(): Promise<CleanupRecommendations> {
  const response = await apiClient.get<CleanupRecommendations>(
    `${BASE_PATH}/cleanup-recommendations`
  );
  return response.data;
}

/**
 * Get storage trends over time.
 */
export async function getStorageTrends(days = 30): Promise<StorageTrend[]> {
  const response = await apiClient.get<StorageTrend[]>(`${BASE_PATH}/trends`, {
    params: { days },
  });
  return response.data;
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook to fetch storage summary with auto-refresh.
 */
export function useStorageSummary(refetchInterval = 60000) {
  return useQuery({
    queryKey: storageKeys.summary(),
    queryFn: getStorageSummary,
    refetchInterval,
    staleTime: 30000,
  });
}

/**
 * Hook to fetch cleanup recommendations.
 */
export function useCleanupRecommendations(enabled = true) {
  return useQuery({
    queryKey: storageKeys.cleanup(),
    queryFn: getCleanupRecommendations,
    enabled,
    staleTime: 300000, // 5 minutes
  });
}

/**
 * Hook to fetch storage trends.
 */
export function useStorageTrends(days = 30, enabled = true) {
  return useQuery({
    queryKey: storageKeys.trends(days),
    queryFn: () => getStorageTrends(days),
    enabled,
    staleTime: 300000, // 5 minutes
  });
}
