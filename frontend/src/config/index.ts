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
} as const;

/**
 * Main configuration object - use this as the default import
 */
export const config = {
  api: API_CONFIG,
  app: APP_CONFIG,
  ui: UI_CONFIG,
  features: FEATURES,

  /** Legacy flat access for gradual migration */
  apiUrl: API_CONFIG.baseUrl,
  basePath: APP_CONFIG.basePath,
} as const;

/**
 * Type-safe configuration access
 */
export type Config = typeof config;

export default config;
