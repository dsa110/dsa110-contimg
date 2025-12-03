/**
 * Batch operations types
 * Defines structures for bulk imaging, calibration, and data operations
 */

/**
 * Types of batch operations supported
 */
export type BatchOperationType =
  | "reimage" // Re-image multiple images with new parameters
  | "recalibrate" // Re-calibrate multiple measurement sets
  | "export" // Export multiple images/sources
  | "archive" // Archive old data
  | "delete" // Delete images/sources
  | "qa_rating" // Bulk QA rating assignment
  | "crossmatch"; // Bulk catalog crossmatching

/**
 * Status of a batch job
 */
export type BatchJobStatus =
  | "pending" // Queued, waiting to start
  | "running" // Currently executing
  | "paused" // Paused by user
  | "completed" // Successfully completed
  | "failed" // Failed with errors
  | "cancelled" // Cancelled by user
  | "partial"; // Completed with some failures

/**
 * Priority levels for batch jobs
 */
export type BatchJobPriority = "low" | "normal" | "high";

/**
 * A single item in a batch operation
 */
export interface BatchItem {
  /** Unique identifier for this item */
  id: string;
  /** Type of resource (image, source, ms, etc.) */
  resourceType: "image" | "source" | "ms" | "calibration";
  /** Resource identifier */
  resourceId: string;
  /** Display name */
  name: string;
  /** Item-specific status */
  status: "pending" | "processing" | "completed" | "failed" | "skipped";
  /** Error message if failed */
  error?: string;
  /** Start time for this item */
  startedAt?: string;
  /** Completion time for this item */
  completedAt?: string;
  /** Result data (e.g., new image ID after re-imaging) */
  result?: Record<string, unknown>;
}

/**
 * Parameters for re-imaging batch operation
 */
export interface ReimageParams {
  /** Briggs weighting robustness parameter (-2 to 2) */
  robust?: number;
  /** Cell size in arcseconds */
  cellSize?: number;
  /** Image size in pixels */
  imageSize?: number;
  /** Number of clean iterations */
  niter?: number;
  /** Clean threshold */
  threshold?: string;
  /** UV range filter */
  uvRange?: string;
  /** Taper parameters */
  taper?: string;
}

/**
 * Parameters for re-calibration batch operation
 */
export interface RecalibrateParams {
  /** Calibrator source to use */
  calibratorId?: string;
  /** Force recalibration even if valid calibration exists */
  force?: boolean;
  /** Reference antenna */
  refAnt?: number;
  /** Solution interval */
  solint?: string;
}

/**
 * Parameters for export batch operation
 */
export interface ExportParams {
  /** Export format */
  format: "fits" | "csv" | "votable" | "json";
  /** Include metadata */
  includeMetadata?: boolean;
  /** Compression */
  compress?: boolean;
  /** Destination path or URL */
  destination?: string;
}

/**
 * Parameters for archive batch operation
 */
export interface ArchiveParams {
  /** Archive destination */
  destination: string;
  /** Delete originals after archiving */
  deleteOriginals?: boolean;
  /** Compression level (0-9) */
  compressionLevel?: number;
}

/**
 * Parameters for QA rating batch operation
 */
export interface QARatingParams {
  /** Rating to assign (1-5) */
  rating: number;
  /** Rating notes */
  notes?: string;
  /** Reviewer name */
  reviewer?: string;
}

/**
 * Union type for all batch operation parameters
 */
export type BatchOperationParams =
  | { type: "reimage"; params: ReimageParams }
  | { type: "recalibrate"; params: RecalibrateParams }
  | { type: "export"; params: ExportParams }
  | { type: "archive"; params: ArchiveParams }
  | { type: "delete"; params: Record<string, never> }
  | { type: "qa_rating"; params: QARatingParams }
  | { type: "crossmatch"; params: { catalogs: string[] } };

/**
 * A batch job
 */
export interface BatchJob {
  /** Unique job identifier */
  id: string;
  /** Type of operation */
  operationType: BatchOperationType;
  /** Job name/description */
  name: string;
  /** Current status */
  status: BatchJobStatus;
  /** Priority level */
  priority: BatchJobPriority;
  /** Operation parameters */
  parameters: BatchOperationParams;
  /** Items to process */
  items: BatchItem[];
  /** User who submitted the job */
  submittedBy: string;
  /** When the job was submitted */
  submittedAt: string;
  /** When the job started executing */
  startedAt?: string;
  /** When the job completed */
  completedAt?: string;
  /** Overall progress (0-100) */
  progress: number;
  /** Number of items completed */
  completedCount: number;
  /** Number of items failed */
  failedCount: number;
  /** Error message if job failed */
  error?: string;
  /** Estimated time remaining in seconds */
  estimatedTimeRemaining?: number;
}

/**
 * Request to create a new batch job
 */
export interface CreateBatchJobRequest {
  /** Type of operation */
  operationType: BatchOperationType;
  /** Job name/description */
  name: string;
  /** Priority level */
  priority?: BatchJobPriority;
  /** Operation parameters */
  parameters: BatchOperationParams;
  /** Resource IDs to process */
  resourceIds: string[];
  /** Resource type */
  resourceType: "image" | "source" | "ms" | "calibration";
}

/**
 * Batch job list filters
 */
export interface BatchJobFilters {
  /** Filter by status */
  status?: BatchJobStatus[];
  /** Filter by operation type */
  operationType?: BatchOperationType[];
  /** Filter by date range */
  dateRange?: {
    start: string;
    end: string;
  };
  /** Filter by submitter */
  submittedBy?: string;
}

/**
 * Batch job statistics
 */
export interface BatchJobStats {
  /** Total jobs */
  total: number;
  /** Jobs by status */
  byStatus: Record<BatchJobStatus, number>;
  /** Jobs by type */
  byType: Record<BatchOperationType, number>;
  /** Currently running jobs */
  running: number;
  /** Jobs in queue */
  queued: number;
  /** Average completion time (ms) */
  avgCompletionTime: number;
}

/**
 * Get display label for operation type
 */
export function getOperationLabel(type: BatchOperationType): string {
  const labels: Record<BatchOperationType, string> = {
    reimage: "Re-Image",
    recalibrate: "Re-Calibrate",
    export: "Export",
    archive: "Archive",
    delete: "Delete",
    qa_rating: "QA Rating",
    crossmatch: "Crossmatch",
  };
  return labels[type];
}

/**
 * Get display label for job status
 */
export function getStatusLabel(status: BatchJobStatus): string {
  const labels: Record<BatchJobStatus, string> = {
    pending: "Pending",
    running: "Running",
    paused: "Paused",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
    partial: "Partial Success",
  };
  return labels[status];
}

/**
 * Get status color class
 */
export function getStatusColorClass(status: BatchJobStatus): string {
  const colors: Record<BatchJobStatus, string> = {
    pending: "text-gray-500 bg-gray-100 dark:bg-gray-800",
    running: "text-blue-600 bg-blue-100 dark:bg-blue-900",
    paused: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900",
    completed: "text-green-600 bg-green-100 dark:bg-green-900",
    failed: "text-red-600 bg-red-100 dark:bg-red-900",
    cancelled: "text-gray-500 bg-gray-100 dark:bg-gray-800",
    partial: "text-orange-600 bg-orange-100 dark:bg-orange-900",
  };
  return colors[status];
}

/**
 * Check if a job can be cancelled
 */
export function canCancelJob(job: BatchJob): boolean {
  return job.status === "pending" || job.status === "running";
}

/**
 * Check if a job can be paused
 */
export function canPauseJob(job: BatchJob): boolean {
  return job.status === "running";
}

/**
 * Check if a job can be resumed
 */
export function canResumeJob(job: BatchJob): boolean {
  return job.status === "paused";
}

/**
 * Check if a job can be retried
 */
export function canRetryJob(job: BatchJob): boolean {
  return job.status === "failed" || job.status === "partial";
}
