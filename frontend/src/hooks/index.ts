/**
 * Hooks barrel export.
 *
 * Re-exports all custom hooks for easier imports:
 * import { useSourceFiltering, useUrlFilterState } from '../hooks';
 */

// Data fetching hooks
export { useImage, useSources, useSource, useJobs, useJob } from "./useQueries";

// Error handling hooks
export { default as useErrorHandler } from "./useErrorHandler";
export { default as useErrorMapping } from "./useErrorMapping";

// Network hooks
export { useNetworkNotifications } from "./useNetworkNotifications";
export { useNetworkStatus } from "./useNetworkStatus";

// Provenance hook
export { default as useProvenance } from "./useProvenance";

// Page-specific hooks
export { useImageDetail } from "./useImageDetail";
export { useSourceFiltering } from "./useSourceFiltering";
export { useUrlFilterState } from "./useUrlFilterState";

// Type exports
export type { UrlFilterState } from "./useUrlFilterState";
export type {
  ConeSearchParams,
  FluxFilterParams,
  AdvancedFilterParams,
  SourceFilterOptions,
} from "./useSourceFiltering";

// ABSURD workflow manager hooks
export {
  absurdQueryKeys,
  useTasks,
  useTask,
  useSpawnTask,
  useCancelTask,
  useRetryTask,
  useQueues,
  useQueueStats,
  useWorkers,
  useWorker,
  useWorkerMetrics,
  useAbsurdMetrics,
  useAbsurdHealth,
  useWorkflows,
  useWorkflow,
  useSpawnWorkflow,
  useCancelWorkflow,
  useDeadLetterTasks,
  useReplayDeadLetterTask,
  usePruneTasks,
} from "./useAbsurdQueries";
