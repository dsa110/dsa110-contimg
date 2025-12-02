/**
 * Storage Monitoring Types
 *
 * TypeScript interfaces for disk usage and storage monitoring.
 */

// =============================================================================
// Directory Storage Types
// =============================================================================

export interface DirectoryUsage {
  /** Directory path */
  path: string;
  /** Human-readable name */
  name: string;
  /** Size in bytes */
  size_bytes: number;
  /** Size formatted (e.g., "1.5 TB") */
  size_formatted: string;
  /** Number of files */
  file_count: number;
  /** Last modified timestamp (ISO) */
  last_modified?: string;
  /** Directory type/category */
  category: "hdf5" | "ms" | "images" | "calibration" | "logs" | "other";
}

export interface DiskPartition {
  /** Mount point */
  mount_point: string;
  /** Device name */
  device: string;
  /** Filesystem type */
  filesystem: string;
  /** Total size in bytes */
  total_bytes: number;
  /** Used size in bytes */
  used_bytes: number;
  /** Free size in bytes */
  free_bytes: number;
  /** Usage percentage (0-100) */
  usage_percent: number;
  /** Total formatted */
  total_formatted: string;
  /** Used formatted */
  used_formatted: string;
  /** Free formatted */
  free_formatted: string;
}

export interface StorageAlert {
  /** Alert severity */
  severity: "info" | "warning" | "critical";
  /** Alert message */
  message: string;
  /** Related path */
  path?: string;
  /** Threshold that was exceeded */
  threshold_percent?: number;
  /** Current usage percent */
  current_percent?: number;
}

export interface StorageSummary {
  /** Disk partitions */
  partitions: DiskPartition[];
  /** Directory breakdowns */
  directories: DirectoryUsage[];
  /** Active storage alerts */
  alerts: StorageAlert[];
  /** Total pipeline data size */
  total_pipeline_data_bytes: number;
  /** Total pipeline data formatted */
  total_pipeline_data_formatted: string;
  /** Timestamp of check */
  checked_at: string;
  /** Check duration in ms */
  check_duration_ms?: number;
}

// =============================================================================
// Cleanup Recommendation Types
// =============================================================================

export interface CleanupCandidate {
  /** File or directory path */
  path: string;
  /** Size in bytes */
  size_bytes: number;
  /** Size formatted */
  size_formatted: string;
  /** Age in days */
  age_days: number;
  /** Last accessed */
  last_accessed?: string;
  /** Reason for recommendation */
  reason: string;
  /** Category */
  category: "old_ms" | "old_images" | "old_logs" | "temp" | "orphaned";
  /** Whether it can be safely deleted */
  safe_to_delete: boolean;
}

export interface CleanupRecommendations {
  /** Cleanup candidates */
  candidates: CleanupCandidate[];
  /** Total reclaimable space in bytes */
  total_reclaimable_bytes: number;
  /** Total reclaimable formatted */
  total_reclaimable_formatted: string;
  /** Recommendations generated at */
  generated_at: string;
}

// =============================================================================
// Storage Trends Types
// =============================================================================

export interface StorageTrendPoint {
  /** Timestamp (ISO) */
  timestamp: string;
  /** Total used bytes */
  used_bytes: number;
  /** Usage percent */
  usage_percent: number;
}

export interface StorageTrend {
  /** Partition mount point */
  mount_point: string;
  /** Trend data points */
  data_points: StorageTrendPoint[];
  /** Growth rate (bytes per day) */
  growth_rate_bytes_per_day: number;
  /** Projected days until full */
  days_until_full?: number;
  /** Start of trend period */
  period_start: string;
  /** End of trend period */
  period_end: string;
}
