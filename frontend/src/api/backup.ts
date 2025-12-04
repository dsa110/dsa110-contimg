/**
 * Backup and Restore API
 *
 * Provides hooks for managing system backups including:
 * - Creating new backups (full or incremental)
 * - Listing backup history
 * - Restoring from backup
 * - Validating backup integrity
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// ============================================================================
// Types
// ============================================================================

/** Backup types */
export type BackupType = "full" | "incremental" | "differential";

/** Backup status */
export type BackupStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/** What data to include in backup */
export interface BackupScope {
  /** Include measurement sets */
  measurement_sets: boolean;
  /** Include images */
  images: boolean;
  /** Include catalogs */
  catalogs: boolean;
  /** Include pipeline configurations */
  pipeline_configs: boolean;
  /** Include job history */
  job_history: boolean;
  /** Include QA ratings */
  qa_ratings: boolean;
}

/** Backup record */
export interface Backup {
  id: string;
  name: string;
  type: BackupType;
  status: BackupStatus;
  scope: BackupScope;
  size_bytes: number;
  size_formatted: string;
  item_count: number;
  created_at: string;
  completed_at?: string;
  created_by: string;
  storage_location: string;
  checksum?: string;
  parent_backup_id?: string;
  notes?: string;
  error_message?: string;
}

/** Backup creation request */
export interface CreateBackupRequest {
  name: string;
  type: BackupType;
  scope: BackupScope;
  notes?: string;
  /** For incremental/differential, the parent backup ID */
  parent_backup_id?: string;
}

/** Restore request */
export interface RestoreRequest {
  backup_id: string;
  /** What to restore (subset of backup scope) */
  scope: Partial<BackupScope>;
  /** Whether to overwrite existing data */
  overwrite_existing: boolean;
  /** Dry run - preview only */
  dry_run: boolean;
  notes?: string;
}

/** Restore job */
export interface RestoreJob {
  id: string;
  backup_id: string;
  backup_name: string;
  status: BackupStatus;
  scope: Partial<BackupScope>;
  items_restored: number;
  items_total: number;
  errors: string[];
  started_at: string;
  completed_at?: string;
  started_by: string;
  notes?: string;
}

/** Restore preview result */
export interface RestorePreview {
  backup_id: string;
  items_to_restore: number;
  conflicts: Array<{
    path: string;
    existing_modified: string;
    backup_modified: string;
  }>;
  missing_dependencies: string[];
  estimated_time_seconds: number;
  warnings: string[];
  can_restore: boolean;
}

/** Backup validation result */
export interface BackupValidation {
  backup_id: string;
  is_valid: boolean;
  checksum_verified: boolean;
  files_verified: number;
  files_corrupted: number;
  corrupted_files: string[];
  validation_time_ms: number;
}

// ============================================================================
// Query Keys
// ============================================================================

export const backupKeys = {
  all: ["backups"] as const,
  lists: () => [...backupKeys.all, "list"] as const,
  list: (filters: Record<string, unknown>) =>
    [...backupKeys.lists(), filters] as const,
  details: () => [...backupKeys.all, "detail"] as const,
  detail: (id: string) => [...backupKeys.details(), id] as const,
  validation: (id: string) => [...backupKeys.all, "validation", id] as const,
  restores: () => [...backupKeys.all, "restores"] as const,
  restore: (id: string) => [...backupKeys.restores(), id] as const,
};

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch list of backups
 */
export function useBackups(options?: {
  type?: BackupType;
  status?: BackupStatus;
  limit?: number;
}) {
  return useQuery({
    queryKey: backupKeys.list(options ?? {}),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.type) params.append("type", options.type);
      if (options?.status) params.append("status", options.status);
      if (options?.limit) params.append("limit", options.limit.toString());

      const response = await apiClient.get<{ backups: Backup[] }>(
        `/v1/backups?${params}`
      );
      return response.data.backups;
    },
    staleTime: 30_000,
  });
}

/**
 * Fetch single backup details
 */
export function useBackup(id: string) {
  return useQuery({
    queryKey: backupKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<Backup>(`/v1/backups/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

/**
 * Create a new backup
 */
export function useCreateBackup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CreateBackupRequest) => {
      const response = await apiClient.post<Backup>("/v1/backups", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: backupKeys.lists() });
    },
  });
}

/**
 * Delete a backup
 */
export function useDeleteBackup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/backups/${id}`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: backupKeys.lists() });
    },
  });
}

/**
 * Validate backup integrity
 */
export function useValidateBackup(id: string) {
  return useQuery({
    queryKey: backupKeys.validation(id),
    queryFn: async () => {
      const response = await apiClient.post<BackupValidation>(
        `/v1/backups/${id}/validate`
      );
      return response.data;
    },
    enabled: false, // Manual trigger only
  });
}

/**
 * Preview restore operation
 */
export function useRestorePreview() {
  return useMutation({
    mutationFn: async (request: RestoreRequest) => {
      const response = await apiClient.post<RestorePreview>(
        `/v1/backups/${request.backup_id}/restore/preview`,
        { ...request, dry_run: true }
      );
      return response.data;
    },
  });
}

/**
 * Execute restore operation
 */
export function useRestore() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: RestoreRequest) => {
      const response = await apiClient.post<RestoreJob>(
        `/v1/backups/${request.backup_id}/restore`,
        request
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: backupKeys.restores() });
    },
  });
}

/**
 * Fetch restore job history
 */
export function useRestoreHistory(limit = 10) {
  return useQuery({
    queryKey: [...backupKeys.restores(), { limit }],
    queryFn: async () => {
      const response = await apiClient.get<{ restores: RestoreJob[] }>(
        `/v1/restores?limit=${limit}`
      );
      return response.data.restores;
    },
    staleTime: 30_000,
  });
}

/**
 * Fetch single restore job
 */
export function useRestoreJob(id: string) {
  return useQuery({
    queryKey: backupKeys.restore(id),
    queryFn: async () => {
      const response = await apiClient.get<RestoreJob>(
        `/v1/restores/${id}`
      );
      return response.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      // Poll while running
      const data = query.state.data;
      if (data && (data.status === "running" || data.status === "pending")) {
        return 3000;
      }
      return false;
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format backup type for display
 */
export function formatBackupType(type: BackupType): string {
  const labels: Record<BackupType, string> = {
    full: "Full Backup",
    incremental: "Incremental",
    differential: "Differential",
  };
  return labels[type];
}

/**
 * Get default backup scope (all enabled)
 */
export function getDefaultBackupScope(): BackupScope {
  return {
    measurement_sets: true,
    images: true,
    catalogs: true,
    pipeline_configs: true,
    job_history: true,
    qa_ratings: true,
  };
}

/**
 * Calculate scope summary
 */
export function getScopeSummary(scope: BackupScope): string {
  const enabled = Object.entries(scope)
    .filter(([, v]) => v)
    .map(([k]) =>
      k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    );
  return enabled.length === 6 ? "All Data" : enabled.join(", ");
}
