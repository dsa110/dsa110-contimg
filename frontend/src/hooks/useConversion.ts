/**
 * React Query hooks for the HDF5→MS Conversion API.
 *
 * These hooks interact with the /api/v1/conversion endpoints
 * to manage the streaming conversion pipeline.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../api/client";

// =============================================================================
// Types
// =============================================================================

export interface ConversionStats {
  total_pending: number;
  total_converting: number;
  total_converted_today: number;
  total_failed_today: number;
  oldest_pending: string | null;
  newest_pending: string | null;
}

export interface PendingGroup {
  group_id: string;
  state: string;
  received_at: string;
  last_update: string;
  expected_subbands: number | null;
  actual_subbands: number;
  is_complete: boolean;
  has_calibrator: boolean | null;
  calibrators: string | null;
  files?: string[];
}

export interface PendingGroupsResponse {
  groups: PendingGroup[];
  total: number;
  complete_count: number;
}

export interface ConversionRequest {
  group_id: string;
  priority?: number;
  force?: boolean;
}

export interface ConversionResponse {
  job_id: string;
  group_id: string;
  status: string;
  message: string;
}

export interface GroupStatus {
  group_id: string;
  state: string;
  received_at: string;
  last_update: string;
  expected_subbands: number | null;
  retry_count: number;
  error: string | null;
  error_message: string | null;
  processing_stage: string | null;
  ms_path: string | null;
}

export interface HDF5File {
  filename: string;
  subband: number;
  timestamp: string;
  size_mb: number;
  group_id: string;
}

export interface HDF5IndexResponse {
  files: HDF5File[];
  total: number;
}

// =============================================================================
// Query Keys
// =============================================================================

export const conversionKeys = {
  all: ["conversion"] as const,
  stats: () => [...conversionKeys.all, "stats"] as const,
  pending: (params?: {
    limit?: number;
    completeOnly?: boolean;
    sinceHours?: number;
  }) => [...conversionKeys.all, "pending", params] as const,
  status: (groupId: string) =>
    [...conversionKeys.all, "status", groupId] as const,
  hdf5Index: (params?: { limit?: number; search?: string }) =>
    [...conversionKeys.all, "hdf5-index", params] as const,
};

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Fetch conversion queue statistics.
 */
export function useConversionStats() {
  return useQuery({
    queryKey: conversionKeys.stats(),
    queryFn: async () => {
      const response = await apiClient.get<ConversionStats>(
        "/conversion/stats"
      );
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

/**
 * Fetch pending HDF5 groups ready for conversion.
 */
export function usePendingGroups(
  limit: number = 50,
  completeOnly: boolean = false,
  includeFiles: boolean = false,
  sinceHours: number = 168 // 7 days
) {
  return useQuery({
    queryKey: conversionKeys.pending({ limit, completeOnly, sinceHours }),
    queryFn: async () => {
      const response = await apiClient.get<PendingGroupsResponse>(
        "/conversion/pending",
        {
          params: {
            limit,
            complete_only: completeOnly,
            include_files: includeFiles,
            since_hours: sinceHours,
          },
        }
      );
      return response.data;
    },
    refetchInterval: 15000, // Refresh every 15 seconds
  });
}

/**
 * Fetch status of a specific group.
 */
export function useGroupStatus(groupId: string | null) {
  return useQuery({
    queryKey: conversionKeys.status(groupId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<GroupStatus>(
        `/conversion/status/${encodeURIComponent(groupId!)}`
      );
      return response.data;
    },
    enabled: !!groupId,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      // Poll while converting
      if (state === "converting" || state === "processing") {
        return 2000;
      }
      return false;
    },
  });
}

/**
 * Fetch HDF5 file index.
 */
export function useHDF5Index(limit: number = 100, search?: string) {
  return useQuery({
    queryKey: conversionKeys.hdf5Index({ limit, search }),
    queryFn: async () => {
      const response = await apiClient.get<HDF5IndexResponse>(
        "/conversion/hdf5-index",
        {
          params: { limit, search },
        }
      );
      return response.data;
    },
    staleTime: 60000, // Cache for 1 minute
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Trigger on-demand conversion of a group.
 */
export function useConvertGroup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ConversionRequest) => {
      const response = await apiClient.post<ConversionResponse>(
        "/conversion/convert",
        request
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: conversionKeys.stats() });
      queryClient.invalidateQueries({ queryKey: conversionKeys.pending() });
      queryClient.invalidateQueries({
        queryKey: conversionKeys.status(data.group_id),
      });
    },
  });
}

/**
 * Bulk convert multiple groups.
 */
export function useBulkConvert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (groupIds: string[]) => {
      // Convert groups sequentially to avoid overwhelming the system
      const results: ConversionResponse[] = [];
      for (const groupId of groupIds) {
        const response = await apiClient.post<ConversionResponse>(
          "/conversion/convert",
          { group_id: groupId }
        );
        results.push(response.data);
      }
      return results;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: conversionKeys.stats() });
      queryClient.invalidateQueries({ queryKey: conversionKeys.pending() });
    },
  });
}
