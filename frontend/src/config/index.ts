/**
 * Centralized Application Configuration
 *
 * All environment variables and configuration constants should be accessed
 * through this module to ensure consistency and ease of maintenance.
 *
 * Usage:
 *   import { config } from '@/config';
 *   const url = `${config.apiUrl}/images`;
 */

/**
 * API Configuration
 */
export const API_CONFIG = {
  /** Base URL for API requests. Falls back to /api/v1 for proxy in development */
  baseUrl: import.meta.env.VITE_API_URL || "/api/v1",

  /** Default request timeout in milliseconds */
  timeout: 10_000, // 10 seconds - balanced for slow network and large responses

  /** Maximum retry attempts for failed requests */
  maxRetries: 3,
} as const;

/**
 * Application Configuration
 */
export const APP_CONFIG = {
  /** Base path for routing (used for GitHub Pages deployment) */
  basePath: import.meta.env.BASE_URL || "/",

  /** Application name */
  name: "DSA-110 Pipeline",

  /** Application version (from package.json if available) */
  version: import.meta.env.VITE_APP_VERSION || "1.0.0",
} as const;

/**
 * UI Configuration
 */
export const UI_CONFIG = {
  /** Maximum number of recent items to track per type */
  maxRecentItems: 10, // Reasonable limit for quick access without clutter

  /** Default page size for paginated lists */
  defaultPageSize: 25, // Balance between reducing requests and viewport scrolling

  /** Default field of view for sky viewer (degrees) */
  defaultFov: 0.25, // Optimized for DSA-110 beam size

  /** Default survey for Aladin Lite viewer */
  defaultSurvey: "P/DSS2/color",
} as const;

/**
 * Query Timing Configuration
 *
 * Centralized timing constants for React Query cache and refetch behavior.
 * Use these instead of hardcoded magic numbers.
 */
export const QUERY_TIMING = {
  /** Stale times - how long data is considered fresh */
  staleTime: {
    /** Real-time data (logs, metrics) - very short */
    realtime: 5_000, // 5 seconds
    /** Frequently changing data (tasks, jobs) */
    short: 10_000, // 10 seconds
    /** Moderately changing data (status, health) */
    medium: 30_000, // 30 seconds
    /** Slowly changing data (pipelines, configs) */
    long: 60_000, // 1 minute
    /** Static/semi-static data (stages, catalogs) */
    extended: 300_000, // 5 minutes
  },

  /** Refetch intervals - how often to poll for updates */
  refetchInterval: {
    /** Aggressive polling for active operations */
    fast: 5_000, // 5 seconds
    /** Standard polling for status updates */
    normal: 10_000, // 10 seconds
    /** Background updates for dashboards */
    slow: 30_000, // 30 seconds
    /** Infrequent checks for stable data */
    lazy: 60_000, // 1 minute
  },

  /** UI update intervals */
  uiInterval: {
    /** Relative time display updates */
    relativeTime: 5_000, // 5 seconds
    /** Service health polling */
    healthCheck: 30_000, // 30 seconds
  },
} as const;

/**
 * Feature Flags
 */
export const FEATURES = {
  /** Enable React Query devtools */
  enableDevtools: import.meta.env.DEV,

  /** Enable verbose logging */
  enableVerboseLogging: import.meta.env.DEV,

  /** Enable Storybook integration */
  enableStorybook: true,

  /** Enable experimental SAMP integration */
  enableSAMP: import.meta.env.VITE_ENABLE_SAMP === "true",

  /** Enable calibration comparison feature */
  enableCalibrationComparison:
    import.meta.env.VITE_ENABLE_CALIBRATION_COMPARISON !== "false",
  /** Enable ABSURD workflow integration (optional service) */
  enableABSURD: import.meta.env.VITE_ENABLE_ABSURD === "true",

  /** Enable CARTA viewer integration */
  enableCARTA: import.meta.env.VITE_ENABLE_CARTA !== "false",

  /** Enable Grafana dashboard embedding */
  enableGrafana: import.meta.env.VITE_ENABLE_GRAFANA !== "false",
} as const;

/**
 * CARTA Viewer Configuration
 */
export const CARTA_CONFIG = {
  /** Base URL for CARTA server (if deployed separately) */
  baseUrl: import.meta.env.VITE_CARTA_URL || "/carta",

  /** API endpoint for CARTA status checks */
  statusEndpoint: "/api/v1/carta/status",
} as const;

/**
 * Grafana Configuration
 */
export const GRAFANA_CONFIG = {
  /** Base URL for Grafana server */
  baseUrl: import.meta.env.VITE_GRAFANA_URL || "http://localhost:3030",

  /** Default organization ID */
  orgId: 1,

  /** Default dashboards */
  dashboards: {
    pipelineOverview: "pipeline-overview",
    systemResources: "node-exporter",
    apiPerformance: "fastapi-metrics",
    streamingConverter: "streaming-converter",
  },
} as const;

/**
 * Main configuration object - use this as the default import
 */
export const config = {
  api: API_CONFIG,
  app: APP_CONFIG,
  ui: UI_CONFIG,
  features: FEATURES,
  carta: CARTA_CONFIG,
  grafana: GRAFANA_CONFIG,
  timing: QUERY_TIMING,

  /** Legacy flat access for gradual migration */
  apiUrl: API_CONFIG.baseUrl,
  basePath: APP_CONFIG.basePath,
} as const;

/**
 * Type-safe configuration access
 */
export type Config = typeof config;

export default config;
