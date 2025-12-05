/**
 * API Module Index
 *
 * Centralized exports for all API hooks and utilities.
 * Import from this barrel file for cleaner imports:
 *
 * @example
 * ```ts
 * import { useSystemHealth, useLogs, apiClient } from '../api';
 * ```
 */

// =============================================================================
// Core API Client
// =============================================================================

export { default as apiClient } from "./client";
export { withRetry, noRetry, fetchProvenanceData } from "./client";
export type { RetryConfig } from "./client";

// API endpoint definitions
export {
  API_BASES,
  API_ENDPOINTS,
  HEALTH_ENDPOINTS,
  IMAGES_ENDPOINTS,
  SOURCES_ENDPOINTS,
  MS_ENDPOINTS,
  JOBS_ENDPOINTS,
  IMAGING_ENDPOINTS,
  CALIBRATOR_IMAGING_ENDPOINTS,
  ABSURD_ENDPOINTS,
} from "./endpoints";

// =============================================================================
// Health & Monitoring
// =============================================================================

export {
  healthKeys,
  useSystemHealth,
  useValidityWindows,
  useValidityTimeline,
  useFluxMonitoring,
  useFluxHistory,
  usePointingStatus,
  useAlerts,
  useAcknowledgeAlert,
} from "./health";

// =============================================================================
// Metrics & Prometheus
// =============================================================================

export {
  metricsKeys,
  useMetricsDashboard,
  usePrometheusQuery,
  useMetricHistory,
} from "./metrics";

// =============================================================================
// Logs
// =============================================================================

export { logKeys, buildLogQueryParams, useLogs, useLogTail } from "./logs";
export type { UseLogTailOptions, UseLogTailResult } from "./logs";

// =============================================================================
// Storage & Cleanup
// =============================================================================

export {
  storageKeys,
  getStorageSummary,
  getCleanupRecommendations,
  getStorageTrends,
  useStorageSummary,
  useCleanupRecommendations,
  useStorageTrends,
} from "./storage";

export {
  cleanupKeys,
  useCleanupDryRun,
  useSubmitCleanup,
  useCleanupHistory,
  useCleanupJob,
} from "./cleanup";
export type {
  CleanupFilters,
  CleanupDryRunResult,
  CleanupSubmitRequest,
  CleanupJob,
} from "./cleanup";

// =============================================================================
// Backup & Restore
// =============================================================================

export {
  backupKeys,
  useBackups,
  useBackup,
  useCreateBackup,
  useDeleteBackup,
  useValidateBackup,
  useRestorePreview,
  useRestore,
  useRestoreHistory,
  useRestoreJob,
  formatBackupType,
} from "./backup";
export type {
  BackupType,
  BackupStatus,
  BackupScope,
  Backup,
  CreateBackupRequest,
  RestoreRequest,
  RestoreJob,
  RestorePreview,
  BackupValidation,
} from "./backup";

// =============================================================================
// Retention Policies
// =============================================================================

export {
  listRetentionPolicies,
  createRetentionPolicy,
  updateRetentionPolicy,
  deleteRetentionPolicy,
  simulateRetentionPolicy,
  executeRetentionPolicy,
  listRetentionExecutions,
} from "./retention";

// =============================================================================
// Alert Policies
// =============================================================================

export {
  alertPolicyKeys,
  useAlertPolicies,
  useAlertPolicy,
  useCreateAlertPolicy,
  useUpdateAlertPolicy,
  useDeleteAlertPolicy,
  useToggleAlertPolicy,
  useAlertPolicyDryRun,
  useAlertSilences,
  useCreateAlertSilence,
} from "./alertPolicies";
export type { AlertPolicyListQuery } from "./alertPolicies";

// =============================================================================
// Triggers
// =============================================================================

export {
  triggerKeys,
  useTriggers,
  useTrigger,
  useTriggerExecutions,
  useRecentExecutions,
  useAvailablePipelines,
  useCreateTrigger,
  useUpdateTrigger,
  useDeleteTrigger,
  useToggleTrigger,
  useExecuteTrigger,
  useTestTrigger,
  formatTriggerEvent,
  getTriggerEventIcon,
  formatConditionOperator,
  formatCronExpression,
  calculateSuccessRate,
} from "./triggers";
export type {
  TriggerEvent,
  TriggerStatus,
  ExecutionStatus,
  ConditionOperator,
  TriggerCondition,
  ScheduleConfig,
  PipelineTrigger,
  TriggerExecution,
  CreateTriggerRequest,
  UpdateTriggerRequest,
  AvailablePipeline,
} from "./triggers";

// =============================================================================
// VO Export
// =============================================================================

export {
  voExportKeys,
  useExportJobs,
  useExportJob,
  useExportColumns,
  useExportPreview,
  useCreateExport,
  useDeleteExport,
  useConeSearch,
  useTAPQuery,
  useTAPQueryStatus,
  formatVOFormat,
  getFormatExtension,
  formatDataType,
  formatFileSize,
} from "./vo-export";
export type {
  VOFormat,
  ExportStatus,
  ExportDataType,
  ExportFilter,
  ExportJob,
  CreateExportRequest,
  ExportColumn,
  ExportPreview,
  TAPResult,
  ConeSearchResult,
} from "./vo-export";

// =============================================================================
// Jupyter Integration
// =============================================================================

export {
  useKernels,
  useKernel,
  useStartKernel,
  useRestartKernel,
  useInterruptKernel,
  useShutdownKernel,
  useNotebooks,
  useNotebook,
  useDeleteNotebook,
  useSessions,
  useCreateSession,
  useDeleteSession,
  useNotebookTemplates,
  useLaunchNotebook,
  useJupyterStats,
  useJupyterUrl,
} from "./jupyter";
export type {
  JupyterKernel,
  JupyterNotebook,
  JupyterSession,
  NotebookTemplate,
  LaunchNotebookRequest,
  JupyterStats,
} from "./jupyter";

// =============================================================================
// Saved Queries
// =============================================================================

export {
  savedQueryKeys,
  useSavedQueries,
  useSavedQuery,
  useCreateSavedQuery,
  useUpdateSavedQuery,
  useDeleteSavedQuery,
  useRecordQueryUsage,
  serializeFilters,
  parseFilters,
  generateShareableUrl,
  filtersEqual,
  getFilterSummary,
  getVisibilityLabel as getQueryVisibilityLabel,
  getVisibilityIcon as getQueryVisibilityIcon,
} from "./savedQueries";
export type {
  QueryVisibility,
  QueryContext,
  SavedQuery,
  SaveQueryRequest,
  SavedQueryFilters,
  PaginationInfo,
  SavedQueriesResponse,
} from "./savedQueries";

// =============================================================================
// Comments
// =============================================================================

export {
  commentKeys,
  useComments,
  useComment,
  useCommentThread,
  useCommentsForTarget,
  useCommentStats,
  useMentionableUsers,
  useCreateComment,
  useUpdateComment,
  useDeleteComment,
  usePinComment,
  useUnpinComment,
  useResolveComment,
} from "./comments";
export type {
  CommentTarget,
  Comment,
  CreateCommentRequest,
  UpdateCommentRequest,
  CommentThread,
  CommentStats,
  CommentSearchParams,
  MentionedUser,
} from "./comments";

// =============================================================================
// Ratings
// =============================================================================

export {
  useRatings,
  useRatingSummary,
  useTargetRatingSummary,
  useSubmitRating,
  useUpdateRating,
  useDeleteRating,
  useRatingStats,
  useRatingQueue,
  useUserRatings,
  useAddToQueue,
  useRemoveFromQueue,
} from "./ratings";
export type {
  RatingTarget,
  RatingCategory,
  QualityFlag,
  Rating,
  RatingSubmission,
  RatingSummary,
  TargetRatingSummary,
  RatingStats,
  QueueItem,
} from "./ratings";

// =============================================================================
// CARTA Integration
// =============================================================================

export {
  cartaKeys,
  useCARTAStatus,
  useCARTASessions,
  useOpenInCARTA,
  useCloseCARTASession,
  getCARTAViewerUrl,
  useCARTAViewerUrl,
} from "./carta";
export type {
  CARTAStatus,
  CARTASession,
  CARTAOpenRequest,
  CARTAOpenResponse,
} from "./carta";

// =============================================================================
// Images
// =============================================================================

export type {
  SaveImageRegionsRequest,
  SaveImageRegionsResponse,
} from "./images";
