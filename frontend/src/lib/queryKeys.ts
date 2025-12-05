/**
 * Centralized Query Key Factories
 *
 * This module provides a single source of truth for all React Query cache keys.
 * Using consistent key factories ensures:
 * - Type-safe key generation
 * - Predictable cache invalidation
 * - Easy refactoring of key structures
 *
 * Pattern: Each domain has a factory object with methods that return readonly tuples.
 *
 * @example
 * ```ts
 * import { pipelineKeys, absurdKeys } from "../lib/queryKeys";
 *
 * // In useQuery
 * useQuery({ queryKey: pipelineKeys.executions() })
 *
 * // In cache invalidation
 * queryClient.invalidateQueries({ queryKey: pipelineKeys.all })
 * ```
 */

// =============================================================================
// Pipeline Query Keys
// =============================================================================

export const pipelineKeys = {
  /** Root key for all pipeline queries */
  all: ["pipeline"] as const,

  /** Registered pipelines list */
  registered: () => ["pipeline", "registered"] as const,

  /** Available pipeline stages */
  stages: () => ["pipeline", "stages"] as const,

  /** Pipeline executions (all) */
  executions: () => ["pipeline", "executions"] as const,

  /** Pipeline executions with filters */
  executionList: (params: { limit?: number; statusFilter?: string }) =>
    ["pipeline", "executions", params] as const,

  /** Single execution by ID */
  execution: (executionId: string) =>
    ["pipeline", "executions", executionId] as const,
} as const;

// =============================================================================
// Re-exports from domain modules
// =============================================================================

// These are re-exported for convenience, allowing imports from a single location.
// The canonical definitions remain in their respective modules.

export { queryKeys } from "../hooks/useQueries";
export { absurdQueryKeys } from "../hooks/useAbsurdQueries";
export { conversionKeys } from "../hooks/useConversion";
export { calibratorImagingKeys } from "../hooks/useCalibratorImaging";
export { calibrationComparisonKeys } from "../hooks/useCalibrationComparison";

// API module keys
export { voExportKeys } from "../api/vo-export";
export { triggerKeys } from "../api/triggers";
export { storageKeys } from "../api/storage";
export { savedQueryKeys } from "../api/savedQueries";
export { metricsKeys } from "../api/metrics";
export { logKeys } from "../api/logs";
export { healthKeys } from "../api/health";
export { commentKeys } from "../api/comments";
export { cleanupKeys } from "../api/cleanup";
export { backupKeys } from "../api/backup";
export { alertPolicyKeys } from "../api/alertPolicies";
export { cartaKeys } from "../api/carta";
