/**
 * Data Cleanup API Hooks
 *
 * Provides hooks for data cleanup operations including:
 * - Dry-run estimation (preview impact before actual cleanup)
 * - Cleanup job submission
 * - Cleanup history tracking
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { components } from "./generated/api";

// Types from backend (with fallbacks if not yet generated)
export interface CleanupFilters {
  /** Filter by minimum age in days */
  min_age_days?: number;
  /** Filter by maximum age in days */
  max_age_days?: number;
  /** Minimum size in bytes */
  min_size_bytes?: number;
  /** Maximum size in bytes */
  max_size_bytes?: number;
  /** Filter by tags */
  tags?: string[];
  /** Filter by status */
  status?: ("pending" | "processed" | "archived" | "deleted")[];
  /** Filter by data type */
  data_type?: ("ms" | "image" | "log" | "temp" | "cache")[];
  /** Include paths matching pattern */
  include_pattern?: string;
  /** Exclude paths matching pattern */
  exclude_pattern?: string;
}

export interface CleanupDryRunResult {
  /** Number of items that would be affected */
  affected_count: number;
  /** Total bytes that would be freed */
  bytes_to_free: number;
  /** Human-readable size string */
  size_formatted: string;
  /** Breakdown by category */
  by_category: Record<string, { count: number; bytes: number }>;
  /** Sample of affected paths (first N) */
  sample_paths: string[];
  /** Any warnings or notices */
  warnings: string[];
  /** Whether user has permission to execute */
  can_execute: boolean;
  /** Retention policy hints if applicable */
  retention_hints?: string[];
}

export interface CleanupSubmitRequest {
  /** Filters defining scope */
  filters: CleanupFilters;
  /** Operation type */
  action: "archive" | "delete";
  /** Audit note explaining reason for cleanup */
  audit_note: string;
  /** Whether to skip confirmation (dangerous) */
  skip_confirmation?: boolean;
}

export interface CleanupJob {
  /** Job ID */
  id: string;
  /** Run ID for job tracking */
  run_id: string;
  /** Current status */
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  /** Filters used */
  filters: CleanupFilters;
  /** Action type */
  action: "archive" | "delete";
  /** User who submitted */
  submitted_by: string;
  /** Timestamp submitted */
  submitted_at: string;
  /** Timestamp completed */
  completed_at?: string;
  /** Items processed */
  items_processed?: number;
  /** Bytes freed */
  bytes_freed?: number;
  /** Error message if failed */
  error?: string;
  /** Audit note */
  audit_note: string;
}

// API base URL
const API_BASE = "/api/v1/cleanup";

/**
 * Perform a dry-run to estimate cleanup impact
 */
async function performDryRun(
  filters: CleanupFilters
): Promise<CleanupDryRunResult> {
  const response = await fetch(`${API_BASE}/dry-run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Dry-run failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Submit a cleanup job
 */
async function submitCleanup(
  request: CleanupSubmitRequest
): Promise<CleanupJob> {
  const response = await fetch(`${API_BASE}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Submit failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get cleanup job history
 */
async function getCleanupHistory(limit = 20): Promise<CleanupJob[]> {
  const response = await fetch(`${API_BASE}/history?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch cleanup history: ${response.status}`);
  }

  return response.json();
}

/**
 * Get cleanup job details
 */
async function getCleanupJob(jobId: string): Promise<CleanupJob> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch cleanup job: ${response.status}`);
  }

  return response.json();
}

// Query keys
export const cleanupKeys = {
  all: ["cleanup"] as const,
  dryRun: (filters: CleanupFilters) =>
    [...cleanupKeys.all, "dry-run", filters] as const,
  history: (limit?: number) => [...cleanupKeys.all, "history", limit] as const,
  job: (id: string) => [...cleanupKeys.all, "job", id] as const,
};

/**
 * Hook to perform a dry-run estimate
 */
export function useCleanupDryRun(
  filters: CleanupFilters | null,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: cleanupKeys.dryRun(filters ?? {}),
    queryFn: () => performDryRun(filters!),
    enabled: options?.enabled !== false && filters !== null,
    staleTime: 30000, // 30 seconds - estimates can change
  });
}

/**
 * Hook to submit a cleanup job
 */
export function useSubmitCleanup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: submitCleanup,
    onSuccess: () => {
      // Invalidate history to show new job
      queryClient.invalidateQueries({ queryKey: cleanupKeys.history() });
    },
  });
}

/**
 * Hook to get cleanup job history
 */
export function useCleanupHistory(limit = 20) {
  return useQuery({
    queryKey: cleanupKeys.history(limit),
    queryFn: () => getCleanupHistory(limit),
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook to get a specific cleanup job
 */
export function useCleanupJob(jobId: string | null) {
  return useQuery({
    queryKey: cleanupKeys.job(jobId ?? ""),
    queryFn: () => getCleanupJob(jobId!),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      // Poll running jobs more frequently
      const job = query.state.data;
      if (job?.status === "running" || job?.status === "pending") {
        return 5000; // 5 seconds
      }
      return false;
    },
  });
}

export default {
  useCleanupDryRun,
  useSubmitCleanup,
  useCleanupHistory,
  useCleanupJob,
};
