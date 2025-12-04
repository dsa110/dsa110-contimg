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
  system: "/v1/health/system",
  /** Docker container health */
  docker: (containerName: string) => `/v1/health/docker/${containerName}`,
  /** Systemd service health */
  systemd: (serviceName: string) => `/v1/health/systemd/${serviceName}`,
  /** Database connectivity */
  databases: "/v1/health/databases",
  /** Active calibration validity windows */
  validityWindows: "/v1/health/validity-windows",
  /** Validity windows timeline view */
  validityTimeline: "/v1/health/validity-windows/timeline",
  /** Flux monitoring summary */
  fluxMonitoring: "/v1/health/flux-monitoring",
  /** Flux monitoring history for a calibrator */
  fluxHistory: (calibratorName: string) =>
    `/v1/health/flux-monitoring/${calibratorName}/history`,
  /** Trigger flux monitoring check */
  fluxMonitoringCheck: "/v1/health/flux-monitoring/check",
  /** Active alerts */
  alerts: "/v1/health/alerts",
  /** Calibration health overview */
  calibration: "/v1/health/calibration",
  /** Nearest calibration solutions */
  calibrationNearest: "/v1/health/calibration/nearest",
  /** Calibration timeline */
  calibrationTimeline: "/v1/health/calibration/timeline",
  /** Calibration apply list */
  calibrationApplylist: "/v1/health/calibration/applylist",
  /** Recent calibration QA */
  calibrationQARecent: "/v1/health/calibration/qa/recent",
  /** Calibration QA stats */
  calibrationQAStats: "/v1/health/calibration/qa/stats",
  /** Calibration QA for specific MS */
  calibrationQA: (msPath: string) =>
    `/v1/health/calibration/qa/${encodeURIComponent(msPath)}`,
  /** GPU health status */
  gpus: "/v1/health/gpus",
  /** Specific GPU health */
  gpu: (gpuId: string) => `/v1/health/gpus/${gpuId}`,
  /** GPU history */
  gpuHistory: (gpuId: string) => `/v1/health/gpus/${gpuId}/history`,
  /** Recent GPU alerts */
  gpuAlertsRecent: "/v1/health/gpus/alerts/recent",
  /** Pointing status */
  pointing: "/v1/health/pointing",
} as const;

// =============================================================================
// Images Endpoints
// =============================================================================

export const IMAGES_ENDPOINTS = {
  /** List all images */
  list: "/v1/images",
  /** Get image detail */
  detail: (imageId: string) => `/v1/images/${imageId}`,
  /** Get image provenance */
  provenance: (imageId: string) => `/v1/images/${imageId}/provenance`,
  /** Get image QA metrics */
  qa: (imageId: string) => `/v1/images/${imageId}/qa`,
  /** Get FITS file */
  fits: (imageId: string) => `/v1/images/${imageId}/fits`,
  /** Get image version chain */
  versions: (imageId: string) => `/v1/images/${imageId}/versions`,
  /** Get image children */
  children: (imageId: string) => `/v1/images/${imageId}/children`,
  /** Re-image with new parameters */
  reimage: (imageId: string) => `/v1/images/${imageId}/reimage`,
  /** Create mask for image */
  createMask: (imageId: string) => `/v1/images/${imageId}/masks`,
  /** List masks for image */
  listMasks: (imageId: string) => `/v1/images/${imageId}/masks`,
  /** Delete a mask */
  deleteMask: (imageId: string, maskId: string) =>
    `/v1/images/${imageId}/masks/${maskId}`,
  /** Create region for image */
  createRegion: (imageId: string) => `/v1/images/${imageId}/regions`,
  /** List regions for image */
  listRegions: (imageId: string) => `/v1/images/${imageId}/regions`,
  /** Get specific region */
  getRegion: (imageId: string, regionId: string) =>
    `/v1/images/${imageId}/regions/${regionId}`,
  /** Delete region */
  deleteRegion: (imageId: string, regionId: string) =>
    `/v1/images/${imageId}/regions/${regionId}`,
} as const;

// =============================================================================
// Sources Endpoints
// =============================================================================

export const SOURCES_ENDPOINTS = {
  /** List all sources */
  list: "/v1/sources",
  /** Get source detail */
  detail: (sourceId: string) => `/v1/sources/${sourceId}`,
  /** Get source lightcurve */
  lightcurve: (sourceId: string) => `/v1/sources/${sourceId}/lightcurve`,
  /** Get source variability metrics */
  variability: (sourceId: string) => `/v1/sources/${sourceId}/variability`,
  /** Get source QA */
  qa: (sourceId: string) => `/v1/sources/${sourceId}/qa`,
} as const;

// =============================================================================
// Measurement Sets (MS) Endpoints
// =============================================================================

export const MS_ENDPOINTS = {
  /** Get MS metadata */
  metadata: (path: string) => `/v1/ms/${encodeURIComponent(path)}/metadata`,
  /** Get calibrator matches */
  calibratorMatches: (path: string) =>
    `/v1/ms/${encodeURIComponent(path)}/calibrator-matches`,
  /** Get MS provenance */
  provenance: (path: string) => `/v1/ms/${encodeURIComponent(path)}/provenance`,
  /** Get raster preview */
  raster: (path: string) => `/v1/ms/${encodeURIComponent(path)}/raster`,
  /** Get antenna layout */
  antennas: (path: string) => `/v1/ms/${encodeURIComponent(path)}/antennas`,
} as const;

// =============================================================================
// Jobs Endpoints
// =============================================================================

export const JOBS_ENDPOINTS = {
  /** List all jobs */
  list: "/v1/jobs",
  /** Get job detail */
  detail: (runId: string) => `/v1/jobs/${runId}`,
  /** Get job provenance */
  provenance: (runId: string) => `/v1/jobs/${runId}/provenance`,
  /** Get job logs */
  logs: (runId: string) => `/v1/jobs/${runId}/logs`,
  /** Re-run a job */
  rerun: (runId: string) => `/v1/jobs/${runId}/rerun`,
} as const;

// =============================================================================
// Queue Endpoints
// =============================================================================

export const QUEUE_ENDPOINTS = {
  /** Get queue status */
  status: "/v1/queue",
  /** List queued jobs */
  jobs: "/v1/queue/jobs",
  /** Get specific queued job */
  job: (jobId: string) => `/v1/queue/jobs/${jobId}`,
  /** Cancel a queued job */
  cancel: (jobId: string) => `/v1/queue/jobs/${jobId}/cancel`,
} as const;

// =============================================================================
// Interactive Imaging Endpoints
// =============================================================================

export const IMAGING_ENDPOINTS = {
  /** Start interactive clean session */
  interactive: "/v1/imaging/interactive",
  /** List active sessions */
  sessions: "/v1/imaging/sessions",
  /** Get session detail */
  session: (sessionId: string) => `/v1/imaging/sessions/${sessionId}`,
  /** Delete/stop session */
  deleteSession: (sessionId: string) => `/v1/imaging/sessions/${sessionId}`,
  /** Cleanup stale sessions */
  cleanup: "/v1/imaging/sessions/cleanup",
  /** Get imaging defaults */
  defaults: "/v1/imaging/defaults",
  /** Get imaging status */
  status: "/v1/imaging/status",
} as const;

// =============================================================================
// Calibrator Imaging Endpoints
// =============================================================================

export const CALIBRATOR_IMAGING_ENDPOINTS = {
  /** List calibrators */
  calibrators: "/v1/calibrator-imaging/calibrators",
  /** Get transits for calibrator */
  transits: (calibratorName: string) =>
    `/v1/calibrator-imaging/calibrators/${calibratorName}/transits`,
  /** Get observations for calibrator */
  observations: (calibratorName: string) =>
    `/v1/calibrator-imaging/calibrators/${calibratorName}/observations`,
  /** Generate MS from observations */
  generateMs: "/v1/calibrator-imaging/generate-ms",
  /** Calibrate an MS */
  calibrate: "/v1/calibrator-imaging/calibrate",
  /** Image an MS */
  image: "/v1/calibrator-imaging/image",
  /** Get job status */
  job: (jobId: string) => `/v1/calibrator-imaging/job/${jobId}`,
  /** Get photometry results */
  photometry: (imagePath: string) =>
    `/v1/calibrator-imaging/photometry/${encodeURIComponent(imagePath)}`,
  /** Health check */
  health: "/v1/calibrator-imaging/health",
  /** Data coverage report */
  dataCoverage: "/v1/calibrator-imaging/data-coverage",
  /** Storage health */
  storageHealth: "/v1/calibrator-imaging/health/storage",
  /** Reconcile storage */
  storageReconcile: "/v1/calibrator-imaging/health/storage/reconcile",
  /** Index orphaned files */
  indexOrphaned: "/v1/calibrator-imaging/health/storage/index-orphaned",
  /** Full storage reconciliation */
  fullReconcile: "/v1/calibrator-imaging/health/storage/full-reconcile",
  /** Services health */
  servicesHealth: "/v1/calibrator-imaging/health/services",
  /** Pipeline metrics */
  metrics: "/v1/calibrator-imaging/metrics",
  /** Active alerts */
  alertsActive: "/v1/calibrator-imaging/alerts/active",
  /** Alert history */
  alertsHistory: "/v1/calibrator-imaging/alerts/history",
  /** Evaluate alerts */
  alertsEvaluate: "/v1/calibrator-imaging/alerts/evaluate",
  /** Pointing status */
  pointingStatus: "/v1/calibrator-imaging/pointing/status",
  /** Pointing transits */
  pointingTransits: "/v1/calibrator-imaging/pointing/transits",
  /** Best calibrator recommendation */
  bestCalibrator: "/v1/calibrator-imaging/pointing/best-calibrator",
  /** Precompute transits */
  precomputeTransits: "/v1/calibrator-imaging/pointing/precompute-transits",
  /** Ensure catalogs are loaded */
  ensureCatalogs: "/v1/calibrator-imaging/pointing/ensure-catalogs",
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
  image: (imageId: string) => `/v1/qa/image/${imageId}`,
  /** Get QA for MS */
  ms: (path: string) => `/v1/qa/ms/${encodeURIComponent(path)}`,
  /** Get QA for job */
  job: (runId: string) => `/v1/qa/job/${runId}`,
} as const;

// =============================================================================
// Calibration Endpoints
// =============================================================================

export const CAL_ENDPOINTS = {
  /** Get calibration table info */
  detail: (path: string) => `/v1/cal/${encodeURIComponent(path)}`,
} as const;

// =============================================================================
// Logs Endpoints
// =============================================================================

export const LOGS_ENDPOINTS = {
  /** Get logs for a run */
  get: (runId: string) => `/v1/logs/${runId}`,
  /** Query logs with filters */
  search: "/v1/logs/search",
  /** Live tail endpoint */
  tail: "/v1/logs/tail",
} as const;

// =============================================================================
// Statistics Endpoints
// =============================================================================

export const STATS_ENDPOINTS = {
  /** Get pipeline statistics */
  overview: "/v1/stats",
} as const;

// =============================================================================
// Cache Endpoints
// =============================================================================

export const CACHE_ENDPOINTS = {
  /** Get cache status */
  status: "/v1/cache",
  /** Invalidate cache entries by pattern */
  invalidate: (pattern: string) => `/v1/cache/invalidate/${pattern}`,
} as const;

// =============================================================================
// Services Endpoints
// =============================================================================

export const SERVICES_ENDPOINTS = {
  /** Get all services status */
  status: "/v1/services/status",
  /** Get specific service status */
  serviceStatus: (port: string) => `/v1/services/status/${port}`,
} as const;

// =============================================================================
// Performance Endpoints
// =============================================================================

export const PERFORMANCE_ENDPOINTS = {
  /** Get benchmarks */
  benchmarks: "/v1/performance/benchmarks",
  /** Get performance summary */
  summary: "/v1/performance/summary",
  /** Get GPU performance */
  gpus: "/v1/performance/gpus",
  /** Get performance trends */
  trends: "/v1/performance/trends",
} as const;

// =============================================================================
// Authentication Endpoints
// =============================================================================

export const AUTH_ENDPOINTS = {
  /** Login */
  login: "/v1/auth/login",
  /** Refresh token */
  refresh: "/v1/auth/refresh",
  /** Logout */
  logout: "/v1/auth/logout",
  /** Get current user */
  me: "/v1/auth/me",
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
