/**
 * Feature Flags Configuration
 *
 * Provides runtime feature toggles for graceful degradation.
 * Features can be disabled without redeploying the frontend.
 *
 * Usage:
 *   import { features, isFeatureEnabled } from './features';
 *   if (isFeatureEnabled('absurd')) { ... }
 *
 * To disable a feature at runtime (via browser console):
 *   window.__DSA_FEATURES__.absurd.enabled = false;
 */

export interface FeatureConfig {
  /** Whether the feature is enabled */
  enabled: boolean;
  /** Message to show when feature is unavailable */
  fallbackMessage: string;
  /** Optional: Endpoint to check for feature availability */
  healthEndpoint?: string;
}

export interface FeatureFlags {
  /** Absurd pipeline queue management */
  absurd: FeatureConfig;
  /** CARTA radio astronomy visualization */
  carta: FeatureConfig;
  /** WebSocket real-time updates (falls back to polling if disabled) */
  websocket: FeatureConfig;
  /** Event streaming and monitoring */
  events: FeatureConfig;
  /** Cache management UI */
  cache: FeatureConfig;
  /** Pipeline DLQ (Dead Letter Queue) operations */
  dlq: FeatureConfig;
}

/**
 * Default feature flag configuration
 *
 * All features enabled by default. Disable at runtime via:
 * - Browser console: window.__DSA_FEATURES__.absurd.enabled = false
 * - Environment variable: VITE_FEATURE_ABSURD=false
 */
const defaultFeatures: FeatureFlags = {
  absurd: {
    enabled: import.meta.env.VITE_FEATURE_ABSURD !== "false",
    fallbackMessage: "Absurd pipeline queue is temporarily unavailable",
    healthEndpoint: "/api/absurd/health",
  },
  carta: {
    enabled: import.meta.env.VITE_FEATURE_CARTA !== "false",
    fallbackMessage: "CARTA visualization service is temporarily unavailable",
    healthEndpoint: "/api/visualization/carta/status",
  },
  websocket: {
    enabled: import.meta.env.VITE_FEATURE_WEBSOCKET !== "false",
    fallbackMessage: "Real-time updates unavailable, using polling",
  },
  events: {
    enabled: import.meta.env.VITE_FEATURE_EVENTS !== "false",
    fallbackMessage: "Event monitoring is temporarily unavailable",
    healthEndpoint: "/api/events/stats",
  },
  cache: {
    enabled: import.meta.env.VITE_FEATURE_CACHE !== "false",
    fallbackMessage: "Cache management is temporarily unavailable",
    healthEndpoint: "/api/cache/stats",
  },
  dlq: {
    enabled: import.meta.env.VITE_FEATURE_DLQ !== "false",
    fallbackMessage: "Dead Letter Queue is temporarily unavailable",
    healthEndpoint: "/api/operations/dlq/stats",
  },
};

// Make features accessible globally for runtime toggling
declare global {
  interface Window {
    __DSA_FEATURES__?: FeatureFlags;
  }
}

// Initialize global features object
if (typeof window !== "undefined") {
  window.__DSA_FEATURES__ = window.__DSA_FEATURES__ ?? { ...defaultFeatures };
}

/**
 * Get the current feature flags (includes any runtime overrides)
 */
export function getFeatures(): FeatureFlags {
  if (typeof window !== "undefined" && window.__DSA_FEATURES__) {
    return window.__DSA_FEATURES__;
  }
  return defaultFeatures;
}

/**
 * Check if a feature is enabled
 */
export function isFeatureEnabled(featureName: keyof FeatureFlags): boolean {
  const features = getFeatures();
  return features[featureName].enabled;
}

/**
 * Get the fallback message for a disabled feature
 */
export function getFeatureFallbackMessage(featureName: keyof FeatureFlags): string {
  const features = getFeatures();
  return features[featureName].fallbackMessage;
}

/**
 * Get the health endpoint for a feature (if defined)
 */
export function getFeatureHealthEndpoint(featureName: keyof FeatureFlags): string | undefined {
  const features = getFeatures();
  return features[featureName].healthEndpoint;
}

/**
 * Disable a feature at runtime
 */
export function disableFeature(featureName: keyof FeatureFlags): void {
  const features = getFeatures();
  features[featureName].enabled = false;
}

/**
 * Enable a feature at runtime
 */
export function enableFeature(featureName: keyof FeatureFlags): void {
  const features = getFeatures();
  features[featureName].enabled = true;
}

/**
 * React hook to check feature status
 * Re-renders when features change is detected
 */
export { useFeatureFlag } from "../hooks/useFeatureFlag";

// Export the features object for direct access
export const features = getFeatures();
export type { FeatureFlags as Features };
