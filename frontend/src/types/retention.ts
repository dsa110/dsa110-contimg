/**
 * Data Retention Policy Types
 *
 * Types for managing data lifecycle policies including age-based,
 * size-based, and manual retention rules.
 */

/**
 * Types of data that can have retention policies applied
 */
export type RetentionDataType =
  | "measurement_set" // Raw MS files
  | "calibration" // Calibration tables
  | "image" // FITS images
  | "source_catalog" // Extracted source catalogs
  | "job_log" // Pipeline job logs
  | "temporary"; // Temporary/scratch files

/**
 * Retention rule trigger types
 */
export type RetentionTriggerType =
  | "age" // Delete after N days
  | "size" // Delete when exceeds size threshold
  | "count" // Keep only N most recent
  | "manual"; // Manual cleanup only

/**
 * Actions to take when retention rule triggers
 */
export type RetentionAction =
  | "delete" // Permanently delete
  | "archive" // Move to archive storage
  | "compress" // Compress in place
  | "notify"; // Notify only, no action

/**
 * Priority levels for retention policies
 */
export type RetentionPriority = "low" | "medium" | "high" | "critical";

/**
 * Status of a retention policy
 */
export type RetentionPolicyStatus =
  | "active"
  | "paused"
  | "disabled"
  | "expired";

/**
 * Individual retention rule configuration
 */
export interface RetentionRule {
  /** Unique identifier for the rule */
  id: string;
  /** Human-readable name */
  name: string;
  /** Detailed description */
  description?: string;
  /** What triggers this rule */
  triggerType: RetentionTriggerType;
  /** Action to take when triggered */
  action: RetentionAction;
  /** Threshold value (days for age, bytes for size, count for count) */
  threshold: number;
  /** Unit for threshold display */
  thresholdUnit: "days" | "hours" | "GB" | "TB" | "count";
  /** Whether this rule is enabled */
  enabled: boolean;
}

/**
 * Complete retention policy
 */
export interface RetentionPolicy {
  /** Unique identifier */
  id: string;
  /** Human-readable name */
  name: string;
  /** Detailed description */
  description?: string;
  /** Data type this policy applies to */
  dataType: RetentionDataType;
  /** Priority (higher priority rules execute first) */
  priority: RetentionPriority;
  /** Current status */
  status: RetentionPolicyStatus;
  /** Rules that make up this policy */
  rules: RetentionRule[];
  /** Optional file pattern to match (glob) */
  filePattern?: string;
  /** Optional minimum file size to consider (bytes) */
  minFileSize?: number;
  /** Optional maximum file size to consider (bytes) */
  maxFileSize?: number;
  /** Exclude files matching these patterns */
  excludePatterns?: string[];
  /** Whether to require confirmation before action */
  requireConfirmation: boolean;
  /** Whether to create backup before deletion */
  createBackupBeforeDelete: boolean;
  /** When this policy was created */
  createdAt: string;
  /** When this policy was last updated */
  updatedAt: string;
  /** Who created this policy */
  createdBy?: string;
  /** When this policy was last executed */
  lastExecutedAt?: string;
  /** Next scheduled execution */
  nextScheduledAt?: string;
}

/**
 * A file/item that would be affected by retention policy
 */
export interface RetentionCandidate {
  /** Unique identifier */
  id: string;
  /** File path or resource identifier */
  path: string;
  /** Display name */
  name: string;
  /** Data type */
  dataType: RetentionDataType;
  /** File size in bytes */
  sizeBytes: number;
  /** When the file was created */
  createdAt: string;
  /** When the file was last accessed */
  lastAccessedAt?: string;
  /** Age in days */
  ageDays: number;
  /** Which rule triggered this candidate */
  triggeredByRule: string;
  /** Action that would be taken */
  action: RetentionAction;
  /** Whether this item is protected from deletion */
  isProtected: boolean;
  /** Reason for protection (if protected) */
  protectionReason?: string;
}

/**
 * Simulation results for a retention policy
 */
export interface RetentionSimulation {
  /** Policy being simulated */
  policyId: string;
  /** When simulation was run */
  simulatedAt: string;
  /** Candidates that would be affected */
  candidates: RetentionCandidate[];
  /** Total number of items affected */
  totalItems: number;
  /** Total size that would be freed (bytes) */
  totalSizeBytes: number;
  /** Items by action type */
  byAction: Record<RetentionAction, number>;
  /** Items by data type */
  byDataType: Record<RetentionDataType, number>;
  /** Estimated time to execute (seconds) */
  estimatedDurationSeconds: number;
  /** Warnings or issues detected */
  warnings: string[];
  /** Whether simulation completed successfully */
  success: boolean;
  /** Error message if simulation failed */
  errorMessage?: string;
}

/**
 * Execution result for a retention policy
 */
export interface RetentionExecution {
  /** Unique execution ID */
  id: string;
  /** Policy that was executed */
  policyId: string;
  /** When execution started */
  startedAt: string;
  /** When execution completed */
  completedAt?: string;
  /** Current status */
  status: "running" | "completed" | "failed" | "cancelled";
  /** Number of items processed */
  itemsProcessed: number;
  /** Number of items affected */
  itemsAffected: number;
  /** Total size freed (bytes) */
  sizeFreedBytes: number;
  /** Number of errors encountered */
  errorCount: number;
  /** Error details */
  errors?: Array<{
    item: string;
    error: string;
  }>;
  /** Who triggered this execution */
  triggeredBy: "schedule" | "manual";
  /** User who triggered (if manual) */
  triggeredByUser?: string;
}

/**
 * Summary statistics for retention
 */
export interface RetentionSummary {
  /** Total number of policies */
  totalPolicies: number;
  /** Number of active policies */
  activePolicies: number;
  /** Number of paused policies */
  pausedPolicies: number;
  /** Recent executions */
  recentExecutions: RetentionExecution[];
  /** Total space managed by policies (bytes) */
  totalManagedSpaceBytes: number;
  /** Space freed in last 30 days (bytes) */
  spaceFreedLast30Days: number;
  /** Next scheduled execution */
  nextScheduledExecution?: {
    policyId: string;
    policyName: string;
    scheduledAt: string;
  };
}

/**
 * Form data for creating/editing a retention policy
 */
export interface RetentionPolicyFormData {
  name: string;
  description?: string;
  dataType: RetentionDataType;
  priority: RetentionPriority;
  status: RetentionPolicyStatus;
  rules: Omit<RetentionRule, "id">[];
  filePattern?: string;
  minFileSize?: number;
  maxFileSize?: number;
  excludePatterns?: string[];
  requireConfirmation: boolean;
  createBackupBeforeDelete: boolean;
}

/**
 * Filter options for listing retention policies
 */
export interface RetentionPolicyFilter {
  status?: RetentionPolicyStatus[];
  dataType?: RetentionDataType[];
  priority?: RetentionPriority[];
  search?: string;
}

/**
 * Data type display metadata
 */
export const DATA_TYPE_LABELS: Record<RetentionDataType, string> = {
  measurement_set: "Measurement Sets",
  calibration: "Calibration Tables",
  image: "FITS Images",
  source_catalog: "Source Catalogs",
  job_log: "Job Logs",
  temporary: "Temporary Files",
};

/**
 * Action display metadata
 */
export const ACTION_LABELS: Record<RetentionAction, string> = {
  delete: "Delete",
  archive: "Archive",
  compress: "Compress",
  notify: "Notify Only",
};

/**
 * Priority display metadata
 */
export const PRIORITY_LABELS: Record<RetentionPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

/**
 * Status display metadata
 */
export const STATUS_LABELS: Record<RetentionPolicyStatus, string> = {
  active: "Active",
  paused: "Paused",
  disabled: "Disabled",
  expired: "Expired",
};

/**
 * Helper to format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Helper to parse threshold based on unit
 */
export function parseThreshold(
  value: number,
  unit: RetentionRule["thresholdUnit"]
): number {
  switch (unit) {
    case "hours":
      return value; // Store as hours
    case "days":
      return value * 24; // Convert to hours
    case "GB":
      return value * 1024 * 1024 * 1024; // Convert to bytes
    case "TB":
      return value * 1024 * 1024 * 1024 * 1024; // Convert to bytes
    case "count":
      return value;
    default:
      return value;
  }
}
