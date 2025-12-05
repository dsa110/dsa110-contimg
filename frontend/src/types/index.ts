/**
 * Centralized type exports.
 *
 * Import types from this barrel file:
 * import { ImageSummary, QAGrade } from '../types';
 */

// API types
export type {
  // Base types
  QAGrade,
  JobStatus,
  BaseEntity,
  WithTimestamps,
  WithProvenance,
  WithCoordinates,
  CalibratorMatch,
  // Image types
  ImageSummary,
  ImageDetail,
  // Source types
  SourceSummary,
  SourceDetail,
  ContributingImage,
  // MS types
  MSMetadata,
  // Job types
  JobSummary,
  JobDetail,
} from "./api";

// Error types
export type { ErrorResponse, ErrorSeverity, MappedError } from "./errors";

// Provenance types
export type { ProvenanceStripProps } from "./provenance";

// Note: Deprecated type aliases (ImageDetailResponse, MSDetailResponse, SourceDetailResponse)
// have been removed. Use ImageDetail, MSMetadata, and SourceDetail instead.

// ABSURD workflow manager types
export type {
  TaskStatus,
  Task,
  TaskListResponse,
  QueueStats,
  WorkerState,
  Worker,
  WorkerListResponse,
  WorkerMetrics,
  AbsurdMetrics,
  AlertLevel,
  Alert,
  AbsurdHealth,
  WorkflowStatus,
  Workflow,
  WorkflowTask,
  WorkflowDetail,
  SpawnTaskRequest,
  SpawnWorkflowRequest,
  CancelTaskRequest,
} from "./absurd";

// Storage monitoring types
export type {
  DirectoryUsage,
  DiskPartition,
  StorageAlert,
  StorageSummary,
  CleanupCandidate,
  CleanupRecommendations,
  StorageTrendPoint,
  StorageTrend,
} from "./storage";

// Calibration QA types
export type {
  CalibrationQAMetrics,
  CalibrationIssue,
  CalibrationComparison,
  PhotometryResult,
  QualityThresholds,
} from "./calibration";
export { DEFAULT_QUALITY_THRESHOLDS } from "./calibration";

// Prometheus metrics types
export type {
  MetricDataPoint,
  MetricSeries,
  PrometheusQueryResult,
  SystemMetric,
  MetricThreshold,
  PipelineMetrics,
  ResourceMetrics,
  ResourceMetricsDetailed,
  MetricsDashboard,
} from "./prometheus";

// Log aggregation types
export type {
  LogEntry,
  LogLevel,
  LogQueryParams,
  LogQueryRequest,
  LogSearchResponse,
  LogTimeRange,
} from "./logs";

// =============================================================================
// Additional domain types (newly consolidated)
// =============================================================================

// Authentication types
export type {
  UserRole,
  User,
  LoginCredentials,
  AuthTokens,
  AuthState,
  Permission,
} from "./auth";

// Health monitoring types
export type {
  ServiceStatusType,
  ServiceHealthStatus,
  HealthSummary,
  SystemHealthReport,
  ValidityWindowInfo,
  ActiveSetInfo,
  ActiveValidityWindows,
  AlertSeverity,
} from "./health";

// Retention policy types
export type {
  RetentionDataType,
  RetentionTriggerType,
  RetentionAction,
  RetentionPriority,
  RetentionPolicyStatus,
  RetentionRule,
  RetentionPolicy,
  RetentionPolicyWithStats,
  RetentionExecutionStatus,
  RetentionSimulationResult,
  RetentionStats,
} from "./retention";
export { formatBytes, ACTION_LABELS, PRIORITY_COLORS } from "./retention";

// Notification types
export type {
  NotificationSeverity,
  NotificationCategory,
  NotificationChannel,
  Notification,
  NotificationPreferences,
} from "./notifications";
export { DEFAULT_NOTIFICATION_PREFERENCES } from "./notifications";

// Batch operation types
export type {
  BatchOperationType,
  BatchJobStatus,
  BatchJobPriority,
  BatchItem,
  CreateBatchJobRequest,
  BatchJob,
  BatchProgress,
} from "./batch";

// Region types (for FITS tools)
export type { RegionShape, RegionFormat, Region } from "./regions";

// VO (Virtual Observatory) types
export type {
  VOTableDataType,
  VOTablePrimitiveValue,
  VOTableField,
  VOTableRow,
  VOTableResource,
  VOTable,
  SAMPConnection,
  SAMPMessage,
  SAMPClient,
  ExportFormat,
  ExportOptions,
} from "./vo";

// Alert policy types
export type {
  AlertComparisonOperator,
  AlertPolicyRule,
  AlertPolicy,
  AlertPolicyInput,
  AlertPolicyListResponse,
  AlertSilence,
  CreateSilenceInput,
  DryRunAlert,
  AlertPolicyDryRunRequest,
  AlertPolicyDryRunResponse,
} from "./alerts";
