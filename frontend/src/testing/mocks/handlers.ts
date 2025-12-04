/**
 * MSW Request Handlers
 *
 * Central location for all API mock handlers used in tests.
 * These handlers define the contract between frontend and backend.
 */

import { http, HttpResponse, delay } from "msw";

// =============================================================================
// Types (imported from components for contract alignment)
// =============================================================================

import type { PipelineStatusResponse } from "../../components/pipeline/PipelineStatusPanel";

// =============================================================================
// ABSURD API Response Types
// =============================================================================

/** Response from /absurd/health/detailed */
interface ABSURDHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  worker_pool_healthy: boolean;
  queue_depth: number;
}

/** Response from /absurd/workers */
interface ABSURDWorkersResponse {
  workers: Array<{ id: string; status: string }>;
  total: number;
}

/** Response from /absurd/queues/stats */
interface ABSURDQueuesStatsResponse {
  queue_depth: number;
}

// =============================================================================
// Mock Data Factories
// =============================================================================

/**
 * Create ABSURD health response.
 */
export function createABSURDHealth(
  overrides: Partial<ABSURDHealthResponse> = {}
): ABSURDHealthResponse {
  return {
    status: "healthy",
    worker_pool_healthy: true,
    queue_depth: 6,
    ...overrides,
  };
}

/**
 * Create ABSURD workers response.
 */
export function createABSURDWorkers(
  overrides: Partial<ABSURDWorkersResponse> = {}
): ABSURDWorkersResponse {
  return {
    workers: [
      { id: "worker-1", status: "active" },
      { id: "worker-2", status: "active" },
    ],
    total: 2,
    ...overrides,
  };
}

/**
 * Create ABSURD queues stats response.
 */
export function createABSURDQueuesStats(
  overrides: Partial<ABSURDQueuesStatsResponse> = {}
): ABSURDQueuesStatsResponse {
  return {
    queue_depth: 6,
    ...overrides,
  };
}

/**
 * Create a pipeline status response with sensible defaults.
 * Override any field as needed for specific test cases.
 */
export function createPipelineStatus(
  overrides: Partial<PipelineStatusResponse> = {}
): PipelineStatusResponse {
  return {
    stages: {
      "convert-uvh5-to-ms": {
        pending: 2,
        running: 1,
        completed: 10,
        failed: 0,
      },
      "calibration-solve": { pending: 0, running: 0, completed: 5, failed: 1 },
      "calibration-apply": { pending: 3, running: 0, completed: 4, failed: 0 },
      imaging: { pending: 1, running: 2, completed: 8, failed: 0 },
      validation: { pending: 0, running: 0, completed: 8, failed: 0 },
      crossmatch: { pending: 0, running: 1, completed: 7, failed: 0 },
      photometry: { pending: 0, running: 0, completed: 7, failed: 0 },
      "catalog-setup": { pending: 0, running: 0, completed: 7, failed: 0 },
      "organize-files": { pending: 0, running: 0, completed: 6, failed: 0 },
    },
    total: { pending: 6, running: 4, completed: 62, failed: 1 },
    worker_count: 2,
    last_updated: new Date().toISOString(),
    is_healthy: true,
    ...overrides,
  };
}

// =============================================================================
// Handler Factories
// =============================================================================

/**
 * Create handlers for ABSURD pipeline endpoints.
 * The PipelineStatusPanel fetches from multiple endpoints:
 * - /absurd/health/detailed
 * - /absurd/workers
 * - /absurd/queues/stats
 */
export function createABSURDHandlers(
  options: {
    health?: ABSURDHealthResponse;
    workers?: ABSURDWorkersResponse;
    queuesStats?: ABSURDQueuesStatsResponse;
    error?: boolean;
    delayMs?: number;
  } = {}
) {
  const {
    health = createABSURDHealth(),
    workers = createABSURDWorkers(),
    queuesStats = createABSURDQueuesStats(),
    error = false,
    delayMs = 0,
  } = options;

  return [
    http.get("*/absurd/health/detailed", async () => {
      if (delayMs > 0) await delay(delayMs);
      if (error) {
        return new HttpResponse(null, { status: 503 });
      }
      return HttpResponse.json(health);
    }),

    http.get("*/absurd/workers", async () => {
      if (delayMs > 0) await delay(delayMs);
      if (error) {
        return new HttpResponse(null, { status: 503 });
      }
      return HttpResponse.json(workers);
    }),

    http.get("*/absurd/queues/stats", async () => {
      if (delayMs > 0) await delay(delayMs);
      if (error) {
        return new HttpResponse(null, { status: 503 });
      }
      return HttpResponse.json(queuesStats);
    }),
  ];
}

/**
 * Legacy handler for direct /absurd/status endpoint (for backwards compatibility).
 */
export function createPipelineStatusHandlers(
  options: {
    status?: PipelineStatusResponse;
    error?: boolean;
    delayMs?: number;
  } = {}
) {
  const {
    status = createPipelineStatus(),
    error = false,
    delayMs = 0,
  } = options;

  return [
    http.get("*/absurd/status", async () => {
      if (delayMs > 0) {
        await delay(delayMs);
      }

      if (error) {
        return HttpResponse.json(
          { error: "Service unavailable" },
          { status: 503 }
        );
      }

      return HttpResponse.json(status);
    }),
  ];
}

// =============================================================================
// Default Handlers
// =============================================================================

/**
 * Default handlers that return successful responses.
 * These are used as baseline handlers and can be overridden per-test.
 */
export const defaultHandlers = [
  ...createABSURDHandlers(),
  ...createPipelineStatusHandlers(),
];
