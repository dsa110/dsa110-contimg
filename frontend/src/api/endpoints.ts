/**
 * Centralized API Endpoint Registry
 *
 * This file serves as the single source of truth for all API endpoint paths.
 * Using this registry ensures consistency between frontend API calls and
 * backend route definitions.
 *
 * IMPORTANT: When backend routes change, update this file first, then run:
 *   npm run test:alignment:check
 *
 * Endpoint naming conventions:
 * - Paths are relative to the API client's baseURL (/api)
 * - Use template literals for dynamic path segments
 * - Group endpoints by resource/domain
 */

// =============================================================================
// API Base Paths
// =============================================================================

/**
 * Base paths for different API subsystems.
 * Note: ABSURD is NOT versioned, while most other APIs are v1.
 */
export const API_BASES = {
  /** Versioned REST API */
  V1: "/v1",
  /** ABSURD task queue (unversioned, mounted at /absurd) */
  ABSURD: "/absurd",
  /** Mosaic API (unversioned, mounted at /api/mosaic) */
  MOSAIC: "/mosaic",
} as const;

// =============================================================================
// Health Monitoring Endpoints
// =============================================================================

export const HEALTH_ENDPOINTS = {
  /** System-wide health status */
  system: "/health/system",
  /** Docker container health */
  docker: (containerName: string) => `/health/docker/${containerName}`,
  /** Systemd service health */
  systemd: (serviceName: string) => `/health/systemd/${serviceName}`,
  /** Database connectivity */
  databases: "/health/databases",
  /** Active calibration validity windows */
  validityWindows: "/health/validity-windows",
  /** Validity windows timeline view */
  validityTimeline: "/health/validity-windows/timeline",
  /** Flux monitoring summary */
  fluxMonitoring: "/health/flux-monitoring",
  /** Flux monitoring history for a calibrator */
  fluxHistory: (calibratorName: string) =>
    `/health/flux-monitoring/${calibratorName}/history`,
  /** Trigger flux monitoring check */
  fluxMonitoringCheck: "/health/flux-monitoring/check",
  /** Active alerts */
  alerts: "/health/alerts",
  /** Calibration health overview */
  calibration: "/health/calibration",
  /** Nearest calibration solutions */
  calibrationNearest: "/health/calibration/nearest",
  /** Calibration timeline */
  calibrationTimeline: "/health/calibration/timeline",
  /** Calibration apply list */
  calibrationApplylist: "/health/calibration/applylist",
  /** Recent calibration QA */
  calibrationQARecent: "/health/calibration/qa/recent",
  /** Calibration QA stats */
  calibrationQAStats: "/health/calibration/qa/stats",
  /** Calibration QA for specific MS */
  calibrationQA: (msPath: string) =>
    `/health/calibration/qa/${encodeURIComponent(msPath)}`,
  /** GPU health status */
  gpus: "/health/gpus",
  /** Specific GPU health */
  gpu: (gpuId: string) => `/health/gpus/${gpuId}`,
  /** GPU history */
  gpuHistory: (gpuId: string) => `/health/gpus/${gpuId}/history`,
  /** Recent GPU alerts */
  gpuAlertsRecent: "/health/gpus/alerts/recent",
  /** Pointing status */
  pointing: "/health/pointing",
} as const;

// =============================================================================
// Images Endpoints
// =============================================================================

export const IMAGES_ENDPOINTS = {
  /** List all images */
  list: "/images",
  /** Get image detail */
  detail: (imageId: string) => `/images/${imageId}`,
  /** Get image provenance */
  provenance: (imageId: string) => `/images/${imageId}/provenance`,
  /** Get image QA metrics */
  qa: (imageId: string) => `/images/${imageId}/qa`,
  /** Get FITS file */
  fits: (imageId: string) => `/images/${imageId}/fits`,
  /** Get image version chain */
  versions: (imageId: string) => `/images/${imageId}/versions`,
  /** Get image children */
  children: (imageId: string) => `/images/${imageId}/children`,
  /** Re-image with new parameters */
  reimage: (imageId: string) => `/images/${imageId}/reimage`,
  /** Create mask for image */
  createMask: (imageId: string) => `/images/${imageId}/masks`,
  /** List masks for image */
  listMasks: (imageId: string) => `/images/${imageId}/masks`,
  /** Delete a mask */
  deleteMask: (imageId: string, maskId: string) =>
    `/images/${imageId}/masks/${maskId}`,
  /** Create region for image */
  createRegion: (imageId: string) => `/images/${imageId}/regions`,
  /** List regions for image */
  listRegions: (imageId: string) => `/images/${imageId}/regions`,
  /** Get specific region */
  getRegion: (imageId: string, regionId: string) =>
    `/images/${imageId}/regions/${regionId}`,
  /** Delete region */
  deleteRegion: (imageId: string, regionId: string) =>
    `/images/${imageId}/regions/${regionId}`,
} as const;

// =============================================================================
// Sources Endpoints
// =============================================================================

export const SOURCES_ENDPOINTS = {
  /** List all sources */
  list: "/sources",
  /** Get source detail */
  detail: (sourceId: string) => `/sources/${sourceId}`,
  /** Get source lightcurve */
  lightcurve: (sourceId: string) => `/sources/${sourceId}/lightcurve`,
  /** Get source variability metrics */
  variability: (sourceId: string) => `/sources/${sourceId}/variability`,
  /** Get source QA */
  qa: (sourceId: string) => `/sources/${sourceId}/qa`,
} as const;

// =============================================================================
// Measurement Sets (MS) Endpoints
// =============================================================================

export const MS_ENDPOINTS = {
  /** Get MS metadata */
  metadata: (path: string) => `/ms/${encodeURIComponent(path)}/metadata`,
  /** Get calibrator matches */
  calibratorMatches: (path: string) =>
    `/ms/${encodeURIComponent(path)}/calibrator-matches`,
  /** Get MS provenance */
  provenance: (path: string) => `/ms/${encodeURIComponent(path)}/provenance`,
  /** Get raster preview */
  raster: (path: string) => `/ms/${encodeURIComponent(path)}/raster`,
  /** Get antenna layout */
  antennas: (path: string) => `/ms/${encodeURIComponent(path)}/antennas`,
} as const;

// =============================================================================
// Jobs Endpoints
// =============================================================================

export const JOBS_ENDPOINTS = {
  /** List all jobs */
  list: "/jobs",
  /** Get job detail */
  detail: (runId: string) => `/jobs/${runId}`,
  /** Get job provenance */
  provenance: (runId: string) => `/jobs/${runId}/provenance`,
  /** Get job logs */
  logs: (runId: string) => `/jobs/${runId}/logs`,
  /** Re-run a job */
  rerun: (runId: string) => `/jobs/${runId}/rerun`,
} as const;

// =============================================================================
// Queue Endpoints
// =============================================================================

export const QUEUE_ENDPOINTS = {
  /** Get queue status */
  status: "/queue",
  /** List queued jobs */
  jobs: "/queue/jobs",
  /** Get specific queued job */
  job: (jobId: string) => `/queue/jobs/${jobId}`,
  /** Cancel a queued job */
  cancel: (jobId: string) => `/queue/jobs/${jobId}/cancel`,
} as const;

// =============================================================================
// Interactive Imaging Endpoints
// =============================================================================

export const IMAGING_ENDPOINTS = {
  /** Start interactive clean session */
  interactive: "/imaging/interactive",
  /** List active sessions */
  sessions: "/imaging/sessions",
  /** Get session detail */
  session: (sessionId: string) => `/imaging/sessions/${sessionId}`,
  /** Delete/stop session */
  deleteSession: (sessionId: string) => `/imaging/sessions/${sessionId}`,
  /** Cleanup stale sessions */
  cleanup: "/imaging/sessions/cleanup",
  /** Get imaging defaults */
  defaults: "/imaging/defaults",
  /** Get imaging status */
  status: "/imaging/status",
} as const;

// =============================================================================
// Calibrator Imaging Endpoints
// =============================================================================

export const CALIBRATOR_IMAGING_ENDPOINTS = {
  /** List calibrators */
  calibrators: "/calibrator-imaging/calibrators",
  /** Get transits for calibrator */
  transits: (calibratorName: string) =>
    `/calibrator-imaging/calibrators/${calibratorName}/transits`,
  /** Get observations for calibrator */
  observations: (calibratorName: string) =>
    `/calibrator-imaging/calibrators/${calibratorName}/observations`,
  /** Generate MS from observations */
  generateMs: "/calibrator-imaging/generate-ms",
  /** Calibrate an MS */
  calibrate: "/calibrator-imaging/calibrate",
  /** Image an MS */
  image: "/calibrator-imaging/image",
  /** Get job status */
  job: (jobId: string) => `/calibrator-imaging/job/${jobId}`,
  /** Get photometry results */
  photometry: (imagePath: string) =>
    `/calibrator-imaging/photometry/${encodeURIComponent(imagePath)}`,
  /** Health check */
  health: "/calibrator-imaging/health",
  /** Data coverage report */
  dataCoverage: "/calibrator-imaging/data-coverage",
  /** Storage health */
  storageHealth: "/calibrator-imaging/health/storage",
  /** Reconcile storage */
  storageReconcile: "/calibrator-imaging/health/storage/reconcile",
  /** Index orphaned files */
  indexOrphaned: "/calibrator-imaging/health/storage/index-orphaned",
  /** Full storage reconciliation */
  fullReconcile: "/calibrator-imaging/health/storage/full-reconcile",
  /** Services health */
  servicesHealth: "/calibrator-imaging/health/services",
  /** Pipeline metrics */
  metrics: "/calibrator-imaging/metrics",
  /** Active alerts */
  alertsActive: "/calibrator-imaging/alerts/active",
  /** Alert history */
  alertsHistory: "/calibrator-imaging/alerts/history",
  /** Evaluate alerts */
  alertsEvaluate: "/calibrator-imaging/alerts/evaluate",
  /** Pointing status */
  pointingStatus: "/calibrator-imaging/pointing/status",
  /** Pointing transits */
  pointingTransits: "/calibrator-imaging/pointing/transits",
  /** Best calibrator recommendation */
  bestCalibrator: "/calibrator-imaging/pointing/best-calibrator",
  /** Precompute transits */
  precomputeTransits: "/calibrator-imaging/pointing/precompute-transits",
  /** Ensure catalogs are loaded */
  ensureCatalogs: "/calibrator-imaging/pointing/ensure-catalogs",
} as const;

// =============================================================================
// ABSURD Task Queue Endpoints (NOT versioned - uses /absurd prefix)
// =============================================================================

export const ABSURD_ENDPOINTS = {
  /** Health check */
  health: "/health",
  /** List all queues */
  queues: "/queues",
  /** Get queue stats */
  queueStats: (queueName: string) => `/queues/${queueName}`,
  /** Spawn a task */
  spawn: "/spawn",
  /** List tasks */
  tasks: "/tasks",
  /** Get task detail */
  task: (taskId: string) => `/tasks/${taskId}`,
  /** Claim a task */
  claim: (queueName: string) => `/claim/${queueName}`,
  /** Complete a task */
  complete: (taskId: string) => `/complete/${taskId}`,
  /** Fail a task */
  fail: (taskId: string) => `/fail/${taskId}`,
  /** Cancel a task */
  cancel: (taskId: string) => `/cancel/${taskId}`,
  /** List workers */
  workers: "/workers",
  /** Get worker detail */
  worker: (workerId: string) => `/workers/${workerId}`,
  /** Get metrics */
  metrics: "/metrics",
  /** Spawn workflow */
  spawnWorkflow: "/workflows/spawn",
  /** List workflows */
  workflows: "/workflows",
  /** Get workflow detail */
  workflow: (workflowId: string) => `/workflows/${workflowId}`,
  /** Cancel workflow */
  cancelWorkflow: (workflowId: string) => `/workflows/${workflowId}/cancel`,
  /** List workflow templates */
  templates: "/workflows/templates",
} as const;

// =============================================================================
// Mosaic Endpoints (NOT versioned - uses /api/mosaic prefix)
// =============================================================================

export const MOSAIC_ENDPOINTS = {
  /** Create a mosaic */
  create: "/mosaic/create",
  /** Get mosaic status */
  status: (name: string) => `/mosaic/status/${name}`,
  /** List mosaics */
  list: "/mosaic/list",
  /** Delete a mosaic */
  delete: (name: string) => `/mosaic/${name}`,
} as const;

// =============================================================================
// QA Endpoints
// =============================================================================

export const QA_ENDPOINTS = {
  /** Get QA for image */
  image: (imageId: string) => `/qa/image/${imageId}`,
  /** Get QA for MS */
  ms: (path: string) => `/qa/ms/${encodeURIComponent(path)}`,
  /** Get QA for job */
  job: (runId: string) => `/qa/job/${runId}`,
} as const;

// =============================================================================
// Calibration Endpoints
// =============================================================================

export const CAL_ENDPOINTS = {
  /** Get calibration table info */
  detail: (path: string) => `/cal/${encodeURIComponent(path)}`,
} as const;

// =============================================================================
// Logs Endpoints
// =============================================================================

export const LOGS_ENDPOINTS = {
  /** Get logs for a run */
  get: (runId: string) => `/logs/${runId}`,
  /** Query logs with filters */
  search: "/logs/search",
  /** Live tail endpoint */
  tail: "/logs/tail",
} as const;

// =============================================================================
// Statistics Endpoints
// =============================================================================

export const STATS_ENDPOINTS = {
  /** Get pipeline statistics */
  overview: "/stats",
} as const;

// =============================================================================
// Cache Endpoints
// =============================================================================

export const CACHE_ENDPOINTS = {
  /** Get cache status */
  status: "/cache",
  /** Invalidate cache entries by pattern */
  invalidate: (pattern: string) => `/cache/invalidate/${pattern}`,
} as const;

// =============================================================================
// Services Endpoints
// =============================================================================

export const SERVICES_ENDPOINTS = {
  /** Get all services status */
  status: "/services/status",
  /** Get specific service status */
  serviceStatus: (port: string) => `/services/status/${port}`,
} as const;

// =============================================================================
// Performance Endpoints
// =============================================================================

export const PERFORMANCE_ENDPOINTS = {
  /** Get benchmarks */
  benchmarks: "/performance/benchmarks",
  /** Get performance summary */
  summary: "/performance/summary",
  /** Get GPU performance */
  gpus: "/performance/gpus",
  /** Get performance trends */
  trends: "/performance/trends",
} as const;

// =============================================================================
// Authentication Endpoints
// =============================================================================

export const AUTH_ENDPOINTS = {
  /** Login */
  login: "/auth/login",
  /** Refresh token */
  refresh: "/auth/refresh",
  /** Logout */
  logout: "/auth/logout",
  /** Get current user */
  me: "/auth/me",
} as const;

// =============================================================================
// Aggregated Export
// =============================================================================

/**
 * All API endpoints organized by domain.
 * Import this for comprehensive access or import specific domain exports above.
 */
export const API_ENDPOINTS = {
  bases: API_BASES,
  health: HEALTH_ENDPOINTS,
  images: IMAGES_ENDPOINTS,
  sources: SOURCES_ENDPOINTS,
  ms: MS_ENDPOINTS,
  jobs: JOBS_ENDPOINTS,
  queue: QUEUE_ENDPOINTS,
  imaging: IMAGING_ENDPOINTS,
  calibratorImaging: CALIBRATOR_IMAGING_ENDPOINTS,
  absurd: ABSURD_ENDPOINTS,
  mosaic: MOSAIC_ENDPOINTS,
  qa: QA_ENDPOINTS,
  cal: CAL_ENDPOINTS,
  logs: LOGS_ENDPOINTS,
  stats: STATS_ENDPOINTS,
  cache: CACHE_ENDPOINTS,
  services: SERVICES_ENDPOINTS,
  performance: PERFORMANCE_ENDPOINTS,
  auth: AUTH_ENDPOINTS,
} as const;

export default API_ENDPOINTS;
